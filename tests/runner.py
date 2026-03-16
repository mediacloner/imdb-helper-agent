#!/usr/bin/env python3
"""
IMDB Helper — Test Runner
=========================
Runs the 200-question benchmark against the live RAG API, evaluates each
answer with an AI judge, and writes structured JSONL logs + a summary JSON.

Usage:
    python3 runner.py [options]

Options:
    --url URL           RAG API base URL (default: http://localhost:8000)
    --category CAT      Only run questions in this category
    --difficulty DIFF   Only run questions at this difficulty
    --ids 1,5,12        Only run specific question IDs (comma-separated)
    --limit N           Run only the first N questions
    --concurrency N     Parallel requests (default: 1)
    --no-video          Skip video recording (playback script still logged)
    --output DIR        Write results to this directory (default: tests/results/<timestamp>)
    --no-judge          Skip AI judge evaluation
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ── local imports ────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
import config
from judge import judge_answer


# ── helpers ──────────────────────────────────────────────────────────────────

QUESTIONS_PATH = Path(__file__).parent / "questions.json"


def load_questions(args) -> list[dict]:
    with open(QUESTIONS_PATH) as f:
        questions = json.load(f)

    if args.category:
        questions = [q for q in questions if q["category"] == args.category]
    if args.difficulty:
        questions = [q for q in questions if q["difficulty"] == args.difficulty]
    if args.ids:
        ids = {int(i) for i in args.ids.split(",")}
        questions = [q for q in questions if q["id"] in ids]
    # Start-from-ID: skip questions with id < start_id
    start_id = int(os.getenv("TEST_START_ID", "0"))
    if start_id > 1:
        questions = [q for q in questions if q["id"] >= start_id]

    if args.limit:
        questions = questions[: args.limit]

    return questions


def _infer_graph_info(response: dict) -> dict:
    """Derive graph-hit / path info from the API response fields."""
    steps = response.get("steps", [])
    start = response.get("start_node_id", "")
    end = response.get("end_node_id", "")

    synthetic_count = sum(1 for s in steps if str(s.get("node_id", "")).startswith("synthetic_"))
    graph_miss = synthetic_count > 0 or not start or start.startswith("synthetic_")

    return {
        "start_node_id": start,
        "end_node_id": end,
        "path_length": len(steps),
        "graph_miss": graph_miss,
        "synthetic_steps": synthetic_count,
        "path_description": " → ".join(
            s.get("description", "?")[:40] for s in steps[:8]
        ) + ("…" if len(steps) > 8 else ""),
    }


def _format_playwright_steps(steps: list[dict]) -> list[dict]:
    """Extract human-readable Playwright step log from API steps."""
    out = []
    for i, s in enumerate(steps):
        action = s.get("action") or {}
        out.append({
            "step": i + 1,
            "description": s.get("description", ""),
            "url": s.get("url", ""),
            "interaction_type": action.get("interaction_type", ""),
            "target": action.get("target_element_id"),
            "node_id": s.get("node_id", ""),
            "synthetic": s.get("synthetic", False),
        })
    return out


def _build_playback_script(steps: list[dict]) -> dict:
    """
    When video recording is OFF, produce a structured playback script that
    describes exactly what Playwright would execute — useful for manual
    reproduction, debugging, and future AI analysis.
    """
    if not steps:
        return {"total_steps": 0, "executable": False, "reason": "no steps returned", "lines": []}

    lines = []
    for i, s in enumerate(steps):
        action = s.get("action") or {}
        itype = action.get("interaction_type", "navigate")
        target = action.get("target_element_id") or ""
        url = s.get("url", "")
        desc = s.get("description", f"Step {i+1}")
        synthetic = s.get("synthetic", False)

        if itype == "search_query":
            human = f'Type "{target}" in the IMDb search bar and press Enter'
            playwright = f'await page.fill("#suggestion-search", "{target}"); await page.keyboard.press("Enter");'
        elif itype == "click":
            human = f'Click on "{target}"'
            playwright = f'await page.click(:text("{target}"));' if target else f"await page.goto('{url}');"
        elif itype == "navigate" and url:
            human = f"Navigate directly to {url}"
            playwright = f"await page.goto('{url}');"
        else:
            human = desc
            playwright = f"# manual step: {desc}"

        lines.append({
            "step": i + 1,
            "description": desc,
            "human_instruction": human,
            "playwright_command": playwright,
            "url": url,
            "interaction_type": itype,
            "target": target,
            "synthetic": synthetic,
            "note": "LLM-generated step (graph had no path)" if synthetic else "from graph path",
        })

    return {
        "total_steps": len(lines),
        "executable": True,
        "video_recorded": False,
        "reason": "video recording was disabled — all steps logged here for manual replay or future recording",
        "lines": lines,
    }


# ── core test function ───────────────────────────────────────────────────────

async def run_one(
    client: httpx.AsyncClient,
    question: dict,
    run_judge: bool,
    skip_video: bool,
    semaphore: asyncio.Semaphore,
) -> dict:
    async with semaphore:
        q_id = question["id"]
        q_text = question["question"]
        ts = datetime.now(timezone.utc).isoformat()
        t0 = time.time()

        result = {
            "id": q_id,
            "category": question["category"],
            "difficulty": question["difficulty"],
            "question": q_text,
            "timestamp": ts,
            "duration_ms": 0,
            # ── RAG response ───────────────────────────────────────────────
            "rag_response": {
                "answer": "",
                "steps": [],
                "start_node_id": "",
                "end_node_id": "",
            },
            # ── Graph internals ────────────────────────────────────────────
            "graph_query": {
                "start_node_id": "",
                "end_node_id": "",
                "path_length": 0,
                "graph_miss": True,
                "synthetic_steps": 0,
                "path_description": "",
            },
            # ── Playwright step log ────────────────────────────────────────
            "playwright_steps": [],
            # ── Video ─────────────────────────────────────────────────────
            "video": {"generated": False, "url": None, "reason": "not_requested"},
            # ── AI Judge ──────────────────────────────────────────────────
            "judge": None,
            # ── Error ─────────────────────────────────────────────────────
            "error": None,
        }

        # ── 1. Call /query ────────────────────────────────────────────────
        try:
            resp = await client.post(
                "/query",
                json={"question": q_text},
                timeout=config.REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            api_data = resp.json()

            raw_steps = api_data.get("steps", [])
            result["rag_response"] = {
                "answer": api_data.get("answer", ""),
                "steps": raw_steps,
                "start_node_id": api_data.get("start_node_id", ""),
                "end_node_id": api_data.get("end_node_id", ""),
            }
            result["graph_query"] = _infer_graph_info(api_data)
            result["playwright_steps"] = _format_playwright_steps(raw_steps)

        except Exception as exc:
            result["error"] = f"query_failed: {exc}"
            result["duration_ms"] = int((time.time() - t0) * 1000)
            return result

        # ── 2. Record video (always, unless --no-video) ───────────────────
        raw_steps = result["rag_response"]["steps"]
        if not skip_video and raw_steps:
            try:
                rec_resp = await client.post(
                    "/record",
                    json={"steps": raw_steps},
                    timeout=300.0,
                )
                rec_resp.raise_for_status()
                rec_data = rec_resp.json()
                video_url = rec_data.get("video_url", "")
                actual_steps = rec_data.get("actual_steps", [])
                result["video"] = {
                    "generated": True,
                    "url": video_url,
                    "reason": "ok",
                    "actual_steps": actual_steps,
                    "playback_script": None,
                }
            except Exception as exc:
                result["video"] = {
                    "generated": False,
                    "url": None,
                    "reason": f"recording failed: {exc}",
                    "playback_script": _build_playback_script(raw_steps),
                }
        else:
            result["video"] = {
                "generated": False,
                "url": None,
                "reason": "skipped via --no-video" if skip_video else "no steps to record",
                "playback_script": _build_playback_script(raw_steps),
            }

        # ── 3. AI Judge (always includes video result) ────────────────────
        if run_judge:
            try:
                judge_result = judge_answer(
                    question=q_text,
                    answer=result["rag_response"]["answer"],
                    steps=result["rag_response"]["steps"],
                    graph_miss=result["graph_query"]["graph_miss"],
                    video_generated=result["video"]["generated"],
                    video_error=None if result["video"]["generated"] else result["video"]["reason"],
                    actual_steps=result["video"].get("actual_steps", []),
                )
                result["judge"] = judge_result
            except Exception as exc:
                result["judge"] = {
                    "scores": {},
                    "overall": 0.0,
                    "pass": False,
                    "reasoning": f"Judge crashed: {exc}",
                    "error": str(exc),
                }

        result["duration_ms"] = int((time.time() - t0) * 1000)
        return result


# ── runs index ───────────────────────────────────────────────────────────────

def _update_runs_index(summary: dict, run_dir: Path) -> None:
    """Keep tests/results/index.json up to date — one entry per completed run."""
    index_path = run_dir.parent / "index.json"
    runs: list[dict] = []
    if index_path.exists():
        try:
            runs = json.loads(index_path.read_text())
        except Exception:
            runs = []

    t = summary.get("totals", {})
    s = summary.get("scores", {})
    entry = {
        "run_id": summary["run_id"],
        "generated_at": summary.get("generated_at", ""),
        "questions": t.get("questions", 0),
        "pass_rate_pct": t.get("pass_rate_pct"),
        "avg_score": s.get("average_overall"),
        "graph_hit_rate_pct": t.get("graph_hit_rate_pct"),
        "videos_recorded": t.get("videos_recorded", 0),
        "errors": t.get("errors", 0),
        "config": summary.get("config", {}),
    }

    # Replace existing entry for same run_id or prepend
    runs = [r for r in runs if r.get("run_id") != entry["run_id"]]
    runs.insert(0, entry)

    index_path.write_text(json.dumps(runs, indent=2, ensure_ascii=False))

    # Also write a JS file the dashboard can load directly (works with file://)
    js_path = run_dir.parent.parent / "dashboard" / "runs_data.js"
    js_path.write_text(
        "// Auto-generated by runner.py — do not edit\n"
        f"window.RUNS_INDEX = {json.dumps(runs, indent=2, ensure_ascii=False)};\n"
    )


# ── summary builder ──────────────────────────────────────────────────────────

def build_summary(results: list[dict], run_id: str, args) -> dict:
    total = len(results)
    errors = [r for r in results if r["error"]]
    judged = [r for r in results if r.get("judge") and r["judge"].get("overall") is not None]
    passed = [r for r in judged if r["judge"].get("pass")]
    graph_hits = [r for r in results if not r["graph_query"]["graph_miss"]]
    videos_ok = [r for r in results if r.get("video", {}).get("generated")]
    videos_fail = [r for r in results if not r.get("video", {}).get("generated") and r.get("video", {}).get("reason", "").startswith("recording failed")]

    # Per-category
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "passed": 0, "scores": [], "errors": 0}
        categories[cat]["total"] += 1
        if r["error"]:
            categories[cat]["errors"] += 1
        if r.get("judge"):
            score = r["judge"].get("overall")
            if score is not None:
                categories[cat]["scores"].append(score)
            if r["judge"].get("pass"):
                categories[cat]["passed"] += 1

    for cat_data in categories.values():
        scores = cat_data["scores"]
        cat_data["avg_score"] = round(sum(scores) / len(scores), 2) if scores else None
        del cat_data["scores"]

    # Per-difficulty
    difficulties = {}
    for r in results:
        diff = r["difficulty"]
        if diff not in difficulties:
            difficulties[diff] = {"total": 0, "passed": 0, "avg_score": None, "_scores": []}
        difficulties[diff]["total"] += 1
        if r.get("judge"):
            score = r["judge"].get("overall")
            if score is not None:
                difficulties[diff]["_scores"].append(score)
            if r["judge"].get("pass"):
                difficulties[diff]["passed"] += 1

    for d in difficulties.values():
        s = d.pop("_scores")
        d["avg_score"] = round(sum(s) / len(s), 2) if s else None

    # Score dimension averages
    dim_totals = {k: [] for k in ("relevance", "completeness", "accuracy", "clarity", "navigation_quality")}
    for r in judged:
        for k, v in r["judge"].get("scores", {}).items():
            if k in dim_totals:
                dim_totals[k].append(v)
    dim_avgs = {k: round(sum(v) / len(v), 2) if v else None for k, v in dim_totals.items()}

    # Timing
    durations = [r["duration_ms"] for r in results if not r["error"]]

    # Top failures
    failures = sorted(
        [r for r in judged if not r["judge"].get("pass")],
        key=lambda r: r["judge"].get("overall", 10),
    )[:20]
    top_failures = [
        {
            "id": r["id"],
            "question": r["question"],
            "category": r["category"],
            "difficulty": r["difficulty"],
            "overall_score": r["judge"].get("overall"),
            "reasoning": r["judge"].get("reasoning", ""),
            "weaknesses": r["judge"].get("weaknesses", []),
        }
        for r in failures
    ]

    all_scores = [r["judge"]["overall"] for r in judged]
    avg_score = round(sum(all_scores) / len(all_scores), 2) if all_scores else None

    return {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "rag_url": args.url,
            "judge_model": config.JUDGE_MODEL,
            "pass_threshold": config.PASS_THRESHOLD,
            "record_video": not args.no_video,
        },
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
            "videos_failed": len(videos_fail),
        },
        "scores": {
            "average_overall": avg_score,
            "dimensions": dim_avgs,
        },
        "timing": {
            "avg_ms": round(sum(durations) / len(durations)) if durations else None,
            "min_ms": min(durations) if durations else None,
            "max_ms": max(durations) if durations else None,
        },
        "by_category": categories,
        "by_difficulty": difficulties,
        "top_failures": top_failures,
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="IMDB Helper Test Runner")
    p.add_argument("--url", default=config.RAG_URL, help="RAG API base URL")
    p.add_argument("--category", help="Filter by category")
    p.add_argument("--difficulty", help="Filter by difficulty")
    p.add_argument("--ids", help="Comma-separated question IDs to run")
    p.add_argument("--limit", type=int, help="Run only first N questions")
    p.add_argument("--concurrency", type=int, default=config.CONCURRENCY)
    p.add_argument("--no-video", action="store_true", default=False,
                   help="Skip video recording (playback script still logged)")
    p.add_argument("--output", default=None, help="Output directory")
    p.add_argument("--no-judge", action="store_true", help="Skip AI judge evaluation")
    return p.parse_args()


async def main():
    args = parse_args()
    questions = load_questions(args)

    if not questions:
        print("No questions matched the filters.", file=sys.stderr)
        sys.exit(1)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(args.output or os.path.join(config.RESULTS_DIR, run_id))
    out_dir.mkdir(parents=True, exist_ok=True)

    results_path = out_dir / "results.jsonl"
    summary_path = out_dir / "summary.json"

    print(f"▶ Run ID : {run_id}")
    print(f"▶ API    : {args.url}")
    print(f"▶ Judge  : {'OFF' if args.no_judge else config.JUDGE_MODEL}")
    print(f"▶ Questions: {len(questions)}")
    print(f"▶ Output : {out_dir}")
    print()

    semaphore = asyncio.Semaphore(args.concurrency)
    results: list[dict] = []

    async with httpx.AsyncClient(base_url=args.url) as client:
        tasks = [
            run_one(client, q, run_judge=not args.no_judge, skip_video=args.no_video, semaphore=semaphore)
            for q in questions
        ]

        with open(results_path, "w") as f:
            completed = 0
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
                f.flush()
                completed += 1

                # Progress line
                judge = result.get("judge") or {}
                score = judge.get("overall")
                passed = judge.get("pass")
                flag = "✓" if passed else ("✗" if passed is False else "–")
                score_str = f"{score:.1f}" if score is not None else "N/A"
                err_str = f" ERROR: {result['error']}" if result["error"] else ""
                graph_str = "MISS" if result["graph_query"]["graph_miss"] else "HIT "
                video_str = "🎬" if result["video"]["generated"] else "📋"
                print(
                    f"[{completed:>3}/{len(questions)}] #{result['id']:>3} [{flag}] score={score_str} "
                    f"graph={graph_str} {video_str} {result['duration_ms']:>5}ms  {result['question'][:55]}{err_str}"
                )

    # Sort results by ID for the summary
    results.sort(key=lambda r: r["id"])
    summary = build_summary(results, run_id, args)

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # Update the global runs index (used by the dashboard menu)
    _update_runs_index(summary, out_dir)

    # Print final summary
    t = summary["totals"]
    s = summary["scores"]
    print()
    print("═" * 65)
    print(f"  Run complete: {run_id}")
    print(f"  Questions  : {t['questions']}  |  Errors: {t['errors']}")
    print(f"  Pass rate  : {t['pass_rate_pct']}%  ({t['passed']}/{t['judged']} judged)")
    print(f"  Avg score  : {s['average_overall']} / 10")
    print(f"  Graph hits : {t['graph_hit_rate_pct']}%  ({t['graph_hits']}/{t['questions']})")
    print(f"  Results    : {results_path}")
    print(f"  Summary    : {summary_path}")
    print("═" * 65)
    print()
    print("  Open the dashboard:")
    print(f"    bash tests/serve.sh")


if __name__ == "__main__":
    asyncio.run(main())
