import json
import os
import shutil
import subprocess
import tempfile
import threading
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from chain import QueryChain
from graph_client import GraphClient
from recorder import record_navigation
from request_logger import log_entry, now_ms
from vector_store import VectorStore

load_dotenv()

# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

_vector_store: Optional[VectorStore] = None
_graph_client: Optional[GraphClient] = None
_query_chain: Optional[QueryChain] = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _vector_store, _graph_client, _query_chain

    _vector_store = VectorStore()
    _graph_client = GraphClient()
    _query_chain = QueryChain(_vector_store, _graph_client)

    # Auto-ingest the IMDb context document so the LLM always has site knowledge.
    # Delete and re-insert all chunks for this file so stale chunks from previous
    # versions of the document don't linger (IDs are positional, so adding/removing
    # lines would otherwise leave orphaned embeddings).
    context_path = "/docs/imdb_context.md"
    if os.path.exists(context_path):
        try:
            try:
                existing_ids = _vector_store._collection.get(
                    where={"filename": "imdb_context.md"}, include=[]
                ).get("ids", [])
                if existing_ids:
                    _vector_store._collection.delete(ids=existing_ids)
            except Exception:
                pass  # collection may be empty — ignore
            _vector_store.ingest_file(context_path, "imdb_context.md")
        except Exception as e:
            print(f"Warning: could not ingest IMDb context: {e}")

    yield

    if _graph_client is not None:
        _graph_client.close()


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

os.makedirs("/app/videos", exist_ok=True)
os.makedirs("/tests/results", exist_ok=True)

app = FastAPI(
    title="IMDB Helper RAG Service",
    description="RAG + LLM Brain service for the IMDB Helper project.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/videos", StaticFiles(directory="/app/videos"), name="videos")
app.mount("/dashboard", StaticFiles(directory="/tests/dashboard", html=True), name="dashboard")
app.mount("/results", StaticFiles(directory="/tests/results"), name="results")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None


class QueryResponse(BaseModel):
    answer: str
    steps: list[dict[str, Any]]
    start_node_id: str
    end_node_id: str


class IngestResponse(BaseModel):
    status: str
    filename: str
    chunks_ingested: str


class HealthResponse(BaseModel):
    status: str


class RecordRequest(BaseModel):
    steps: list[dict[str, Any]]


class RecordResponse(BaseModel):
    video_url: str
    actual_steps: list[dict] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/record", response_model=RecordResponse)
async def record(request: RecordRequest) -> RecordResponse:
    """Record a Playwright video navigating through the given steps."""
    if not request.steps:
        raise HTTPException(status_code=422, detail="No steps provided")
    t0 = now_ms()
    rec = await record_navigation(request.steps)
    duration_ms = now_ms() - t0
    video_path = rec.get("path") if rec else None
    actual_steps = rec.get("actual_steps", []) if rec else []
    if not video_path:
        log_entry("record_failed", {"steps": request.steps, "error": "No video file produced"}, duration_ms=duration_ms)
        raise HTTPException(status_code=500, detail="Video recording failed")
    filename = os.path.basename(video_path)
    video_url = f"/videos/{filename}"
    log_entry("record_success", {"video_url": video_url, "actual_steps": len(actual_steps)}, duration_ms=duration_ms)
    return {"video_url": video_url, "actual_steps": actual_steps}


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness check."""
    return HealthResponse(status="ok")


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest) -> QueryResponse:
    """Accept a natural-language question and return a step-by-step navigation answer."""
    if _query_chain is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    if not request.question.strip():
        raise HTTPException(status_code=422, detail="Question must not be empty")

    t0 = now_ms()
    result: dict[str, Any] = _query_chain.run(request.question)
    duration_ms = now_ms() - t0

    log_entry("query", {
        "question": request.question,
        "llm_intent": result.get("intent", {}),
        "graph_miss": result.get("graph_miss", False),
        "synthetic_steps": result.get("synthetic_steps", False),
        "steps_count": len(result.get("steps", [])),
        "steps": result.get("steps", []),
        "answer": result.get("answer", ""),
        "start_node_id": result.get("start_node_id", ""),
        "end_node_id": result.get("end_node_id", ""),
    }, duration_ms=duration_ms)

    return QueryResponse(
        answer=result.get("answer", ""),
        steps=result.get("steps", []),
        start_node_id=result.get("start_node_id", ""),
        end_node_id=result.get("end_node_id", ""),
    )


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

TESTS_DIR = Path("/tests")
_test_runs: dict[str, dict] = {}


class TestRunRequest(BaseModel):
    category: Optional[str] = None
    difficulty: Optional[str] = None
    ids: Optional[str] = None
    limit: Optional[int] = None
    no_judge: bool = False
    no_video: bool = False


def _count_questions(req: TestRunRequest) -> int:
    q_path = TESTS_DIR / "questions.json"
    if not q_path.exists():
        return 0
    with open(q_path) as f:
        questions = json.load(f)
    if req.category:
        questions = [q for q in questions if q["category"] == req.category]
    if req.difficulty:
        questions = [q for q in questions if q["difficulty"] == req.difficulty]
    if req.ids:
        ids = {int(i) for i in req.ids.split(",") if i.strip().isdigit()}
        questions = [q for q in questions if q["id"] in ids]
    if req.limit:
        questions = questions[: req.limit]
    return len(questions)


@app.post("/tests/run")
async def tests_run(request: TestRunRequest):
    """Start a test run in the background and return a run_id to poll."""
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = TESTS_DIR / "results" / run_id

    total = _count_questions(request)
    if total == 0:
        raise HTTPException(status_code=400, detail="No questions matched the filters")

    cmd = [
        "python3",
        str(TESTS_DIR / "runner.py"),
        "--url", "http://localhost:8000",
        "--output", str(output_dir),
    ]
    if request.category:
        cmd += ["--category", request.category]
    if request.difficulty:
        cmd += ["--difficulty", request.difficulty]
    if request.ids:
        cmd += ["--ids", request.ids]
    if request.limit:
        cmd += ["--limit", str(request.limit)]
    if request.no_judge:
        cmd += ["--no-judge"]
    if request.no_video:
        cmd += ["--no-video"]

    proc = subprocess.Popen(
        cmd,
        env={**os.environ, "RAG_URL": "http://localhost:8000"},
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    _test_runs[run_id] = {
        "run_id": run_id,
        "status": "running",
        "total": total,
        "process": proc,
        "started_at": datetime.now().isoformat(),
    }

    def _watch(rid: str, p: subprocess.Popen) -> None:
        p.wait()
        if rid in _test_runs:
            _test_runs[rid]["status"] = "done" if p.returncode == 0 else "error"

    threading.Thread(target=_watch, args=(run_id, proc), daemon=True).start()
    return {"run_id": run_id, "total": total}


@app.get("/tests/status/{run_id}")
async def tests_status(run_id: str):
    """Poll the progress of a running (or completed) test run, including the last 3 results."""
    output_dir = TESTS_DIR / "results" / run_id
    jsonl_path = output_dir / "results.jsonl"
    summary_path = output_dir / "summary.json"

    completed = 0
    recent: list[dict] = []
    if jsonl_path.exists():
        lines = [l for l in jsonl_path.read_text().splitlines() if l.strip()]
        completed = len(lines)
        for raw in lines[-3:]:
            try:
                r = json.loads(raw)
                overall = r.get("judge", {}).get("overall") if r.get("judge") else None
                recent.append({
                    "id": r.get("id"),
                    "question": r.get("question", "")[:80],
                    "category": r.get("category", ""),
                    "difficulty": r.get("difficulty", ""),
                    "overall": overall,
                    "passed": r.get("judge", {}).get("pass") if r.get("judge") else None,
                    "graph_miss": r.get("graph_query", {}).get("graph_miss", True),
                    "video": r.get("video", {}).get("generated", False),
                    "error": r.get("error"),
                    "duration_ms": r.get("duration_ms", 0),
                })
            except Exception:
                pass

    run = _test_runs.get(run_id)
    if run:
        status = run["status"]
        if summary_path.exists() and status == "running":
            run["status"] = "done"
            status = "done"
        return {
            "run_id": run_id,
            "status": status,
            "total": run["total"],
            "completed": completed,
            "started_at": run.get("started_at"),
            "recent": recent,
        }

    # Run not in memory (server restarted); infer from disk
    if output_dir.exists():
        return {
            "run_id": run_id,
            "status": "done" if summary_path.exists() else "unknown",
            "total": completed,
            "completed": completed,
            "started_at": None,
            "recent": recent,
        }

    raise HTTPException(status_code=404, detail="Run not found")


def _build_partial_summary(run_id: str, output_dir: Path) -> None:
    """Build and save a summary.json from whatever results.jsonl was written so far."""
    jsonl_path = output_dir / "results.jsonl"
    summary_path = output_dir / "summary.json"
    if summary_path.exists() or not jsonl_path.exists():
        return
    results = []
    for line in jsonl_path.read_text().splitlines():
        if line.strip():
            try:
                results.append(json.loads(line))
            except Exception:
                pass
    if not results:
        return

    total = len(results)
    errors = [r for r in results if r.get("error")]
    judged = [r for r in results if r.get("judge") and r["judge"].get("overall") is not None]
    passed = [r for r in judged if r["judge"].get("pass")]
    graph_hits = [r for r in results if not r.get("graph_query", {}).get("graph_miss", True)]
    videos_ok = [r for r in results if r.get("video", {}).get("generated")]

    all_scores = [r["judge"]["overall"] for r in judged]
    avg_score = round(sum(all_scores) / len(all_scores), 2) if all_scores else None

    dim_keys = ["relevance", "completeness", "accuracy", "clarity", "navigation_quality", "executability"]
    dim_totals: dict = {k: [] for k in dim_keys}
    for r in judged:
        for k in dim_keys:
            v = r["judge"].get("scores", {}).get(k)
            if v is not None:
                dim_totals[k].append(v)
    dim_avgs = {k: round(sum(v) / len(v), 2) if v else None for k, v in dim_totals.items()}

    by_cat: dict = {}
    by_diff: dict = {}
    for r in results:
        for grp, key in [(by_cat, r.get("category", "")), (by_diff, r.get("difficulty", ""))]:
            if key not in grp:
                grp[key] = {"total": 0, "passed": 0, "errors": 0, "_s": []}
            grp[key]["total"] += 1
            if r.get("error"):
                grp[key]["errors"] += 1
            if r.get("judge") and r["judge"].get("overall") is not None:
                grp[key]["_s"].append(r["judge"]["overall"])
                if r["judge"].get("pass"):
                    grp[key]["passed"] += 1
    for grp in (by_cat, by_diff):
        for v in grp.values():
            scores = v.pop("_s")
            v["avg_score"] = round(sum(scores) / len(scores), 2) if scores else None
            judged_n = v["total"] - v["errors"]
            v["pass_rate_pct"] = round(100 * v["passed"] / judged_n, 1) if judged_n else None

    failures = sorted(
        [r for r in judged if not r["judge"].get("pass")],
        key=lambda r: r["judge"].get("overall", 10),
    )[:10]

    summary = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "partial": True,
        "config": {"rag_url": "http://localhost:8000", "record_video": True},
        "totals": {
            "questions": total,
            "answered": total - len(errors),
            "errors": len(errors),
            "judged": len(judged),
            "passed": len(passed),
            "failed": len(judged) - len(passed),
            "pass_rate_pct": round(100 * len(passed) / len(judged), 1) if judged else None,
            "graph_hits": len(graph_hits),
            "graph_misses": total - len(graph_hits),
            "graph_hit_rate_pct": round(100 * len(graph_hits) / total, 1) if total else None,
            "videos_recorded": len(videos_ok),
            "videos_failed": 0,
        },
        "scores": {"average_overall": avg_score, "dimensions": dim_avgs},
        "by_category": by_cat,
        "by_difficulty": by_diff,
        "top_failures": [
            {"id": r["id"], "question": r["question"], "category": r["category"],
             "difficulty": r["difficulty"], "overall_score": r["judge"].get("overall"),
             "reasoning": r["judge"].get("reasoning", ""),
             "weaknesses": r["judge"].get("weaknesses", [])}
            for r in failures
        ],
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    # Update index.json
    index_path = output_dir.parent / "index.json"
    runs: list = []
    if index_path.exists():
        try:
            runs = json.loads(index_path.read_text())
        except Exception:
            pass
    entry = {
        "run_id": run_id,
        "generated_at": summary["generated_at"],
        "questions": total,
        "pass_rate_pct": summary["totals"]["pass_rate_pct"],
        "avg_score": avg_score,
        "graph_hit_rate_pct": summary["totals"]["graph_hit_rate_pct"],
        "videos_recorded": len(videos_ok),
        "errors": len(errors),
        "partial": True,
    }
    runs = [r for r in runs if r.get("run_id") != run_id]
    runs.insert(0, entry)
    index_path.write_text(json.dumps(runs, indent=2, ensure_ascii=False))


@app.post("/tests/stop/{run_id}")
async def tests_stop(run_id: str):
    """Stop a running test run and save a partial summary of completed questions."""
    run = _test_runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found or already finished")
    proc: subprocess.Popen = run.get("process")
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    run["status"] = "stopped"
    output_dir = TESTS_DIR / "results" / run_id
    _build_partial_summary(run_id, output_dir)
    return {"run_id": run_id, "status": "stopped"}


@app.delete("/tests/runs/{run_id}")
async def tests_delete_run(run_id: str):
    """Delete a test run's result files and its associated videos."""
    output_dir = TESTS_DIR / "results" / run_id
    # If the directory is already gone, still clean up the index — don't 404

    # Delete associated video files
    jsonl_path = output_dir / "results.jsonl"
    if jsonl_path.exists():
        for line in jsonl_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
                video_url = r.get("video", {}).get("url", "")
                if video_url:
                    video_file = Path("/app/videos") / Path(video_url).name
                    if video_file.exists():
                        video_file.unlink()
            except Exception:
                pass

    shutil.rmtree(output_dir, ignore_errors=True)

    # Remove from index.json
    index_path = TESTS_DIR / "results" / "index.json"
    if index_path.exists():
        try:
            runs = json.loads(index_path.read_text())
            runs = [r for r in runs if r.get("run_id") != run_id]
            index_path.write_text(json.dumps(runs, indent=2, ensure_ascii=False))
        except Exception:
            pass

    _test_runs.pop(run_id, None)
    return {"run_id": run_id, "status": "deleted"}


@app.get("/tests/runs")
async def tests_list():
    """Return the list of all completed test runs from the index."""
    index_path = TESTS_DIR / "results" / "index.json"
    if not index_path.exists():
        return []
    with open(index_path) as f:
        return json.load(f)


@app.get("/tests/runs/{run_id}")
async def tests_run_summary(run_id: str):
    """Return the summary JSON for a specific completed run."""
    summary_path = TESTS_DIR / "results" / run_id / "summary.json"
    if not summary_path.exists():
        raise HTTPException(status_code=404, detail="Run not found or not complete yet")
    with open(summary_path) as f:
        return json.load(f)


@app.post("/ingest", response_model=IngestResponse)
async def ingest(file: UploadFile = File(...)) -> IngestResponse:
    """Accept a text/markdown/PDF file upload and ingest it into the vector store."""
    if _vector_store is None:
        raise HTTPException(status_code=503, detail="Service not ready")

    allowed_content_types = {
        "text/plain",
        "text/markdown",
        "application/pdf",
        "application/octet-stream",
    }
    content_type = file.content_type or "application/octet-stream"
    if content_type not in allowed_content_types and not content_type.startswith("text/"):
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {content_type}. Use text, markdown, or PDF.",
        )

    filename: str = file.filename or "uploaded_file"

    file_bytes: bytes = await file.read()

    suffix = os.path.splitext(filename)[1] or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_bytes)
        tmp_path: str = tmp.name

    try:
        _vector_store.ingest_file(tmp_path, filename)
    finally:
        os.unlink(tmp_path)

    return IngestResponse(
        status="ok",
        filename=filename,
        chunks_ingested="ingested",
    )
