import os
import tempfile
from contextlib import asynccontextmanager
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

    # Auto-ingest the IMDb context document so the LLM always has site knowledge
    context_path = "/docs/imdb_context.md"
    if os.path.exists(context_path):
        try:
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

app = FastAPI(
    title="IMDB Helper RAG Service",
    description="RAG + LLM Brain service for the IMDB Helper project.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/videos", StaticFiles(directory="/app/videos"), name="videos")

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


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/record", response_model=RecordResponse)
async def record(request: RecordRequest) -> RecordResponse:
    """Record a Playwright video navigating through the given steps."""
    if not request.steps:
        raise HTTPException(status_code=422, detail="No steps provided")
    t0 = now_ms()
    video_path = await record_navigation(request.steps)
    duration_ms = now_ms() - t0
    if not video_path:
        log_entry("record_failed", {"steps": request.steps, "error": "Video recording returned no file"}, duration_ms=duration_ms)
        raise HTTPException(status_code=500, detail="Video recording failed")
    filename = os.path.basename(video_path)
    video_url = f"/videos/{filename}"
    log_entry("record_success", {"steps": request.steps, "video_url": video_url}, duration_ms=duration_ms)
    return RecordResponse(video_url=video_url)


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
