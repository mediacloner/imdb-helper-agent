"""AI Judge — evaluates the quality of a RAG answer using Ollama."""
import json
import re
import httpx

import config

_JUDGE_PROMPT = """You are an expert evaluator of AI-powered navigation assistants for the IMDb website.

You will receive:
1. The user question
2. The AI's text answer and planned navigation steps
3. ACTUAL BROWSER TRACE — the real URLs and page titles the browser visited during execution

The ACTUAL BROWSER TRACE is ground truth. Use it to detect when the browser went somewhere wrong.

CRITICAL RULES:
- If the actual trace shows pages unrelated to the question (e.g. podcast pages when asked about short films, wrong titles, sign-in page instead of content), score executability and navigation_quality LOW (0-3).
- If the actual trace shows the browser visiting correct pages matching the question intent, that is strong evidence of quality.
- If the actual trace shows repeated visits to the same wrong page, score very low.
- If no actual trace is provided, evaluate based on planned steps only and be more conservative.
- NEVER give high executability scores just because a video was recorded — only if the actual URLs match the question's intent.

Evaluate the quality on SIX dimensions (each 0-10):

1. **relevance** — Does the answer directly address what the user asked?
2. **completeness** — Are all necessary steps present? Nothing missing?
3. **accuracy** — Is the navigation path correct for IMDb? Score 0-2 if actual trace shows wrong pages.
4. **clarity** — Is the answer easy for a human to follow?
5. **navigation_quality** — Do the actual URLs visited match the question's goal?
   - Check the actual trace: did the browser reach the right section of IMDb?
6. **executability** — Did the execution actually reach the correct destination?
   - Score 8-10: actual trace shows correct pages matching the question
   - Score 4-7: trace is partial or somewhat related
   - Score 0-3: trace shows wrong pages, repeated errors, or unrelated content

Scoring guide:
- 9-10: Perfect — actual trace confirms correct navigation
- 7-8: Good — mostly correct with minor issues
- 5-6: Acceptable — partially correct
- 3-4: Poor — significant navigation errors visible in trace
- 0-2: Wrong — actual trace shows completely unrelated pages

Respond ONLY with a valid JSON object — no text outside it:
{
  "scores": {
    "relevance": <0-10>,
    "completeness": <0-10>,
    "accuracy": <0-10>,
    "clarity": <0-10>,
    "navigation_quality": <0-10>,
    "executability": <0-10>
  },
  "overall": <0-10 weighted average>,
  "pass": <true if overall >= 6.0>,
  "strengths": ["<one-line strength>", "..."],
  "weaknesses": ["<one-line weakness>", "..."],
  "reasoning": "<2-3 sentences explaining the evaluation, referencing actual URLs if relevant>"
}"""


def _call_ollama(messages: list[dict]) -> str:
    """Synchronous call to Ollama /api/chat."""
    payload = {
        "model": config.JUDGE_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.0},
        "think": False,
        "format": "json",
    }
    with httpx.Client(timeout=120.0) as client:
        response = client.post(f"{config.OLLAMA_URL}/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        return data.get("message", {}).get("content", "")


def _strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def judge_answer(
    question: str,
    answer: str,
    steps: list[dict],
    graph_miss: bool = False,
    video_generated: bool = False,
    video_error: str | None = None,
    actual_steps: list[dict] | None = None,
) -> dict:
    """
    Evaluate an answer+steps pair and return a structured judgement dict.
    On any error returns a fallback with all scores at 0.
    """
    # Summarise steps for the prompt (avoid huge payloads)
    step_lines = []
    for i, s in enumerate(steps[:20]):
        action = s.get("action") or {}
        itype = action.get("interaction_type", "?")
        target = action.get("target_element_id") or ""
        url = s.get("url", "")
        desc = s.get("description", "")
        step_lines.append(f"  Step {i+1}: [{itype}] {desc} | target={target!r} | url={url!r}")
    steps_text = "\n".join(step_lines) if step_lines else "  (no steps)"

    graph_note = (
        "NOTE: The graph had no matching path; the answer was generated synthetically by the LLM."
        if graph_miss
        else "NOTE: The answer was derived from a graph path."
    )

    if video_generated:
        video_note = (
            "VIDEO RECORDING: Playwright ran without crashing (technical execution only). "
            "This does NOT mean the navigation was correct — judge executability based on "
            "whether the steps navigate to the right destination for the question asked."
        )
    elif video_error:
        video_note = f"VIDEO RECORDING: Failed — {video_error}"
    else:
        video_note = "VIDEO RECORDING: Not attempted."

    actual_trace_lines = []
    for s in (actual_steps or [])[:20]:
        actual_trace_lines.append(
            f"  Step {s.get('step', '?') + 1}: {s.get('actual_title', '')!r} | {s.get('actual_url', '')} [{s.get('method', '')}]"
        )
    actual_trace_text = "\n".join(actual_trace_lines) if actual_trace_lines else "  (not available)"

    user_content = (
        f"User question: {question}\n\n"
        f"AI answer:\n{answer}\n\n"
        f"Planned navigation steps:\n{steps_text}\n\n"
        f"ACTUAL BROWSER TRACE (real URLs visited during execution):\n{actual_trace_text}\n\n"
        f"{graph_note}\n"
        f"{video_note}"
    )

    try:
        raw = _call_ollama([
            {"role": "system", "content": _JUDGE_PROMPT},
            {"role": "user", "content": user_content},
        ])
        raw = _strip_think(raw)
        result = json.loads(raw)

        # Normalise: ensure all keys exist
        scores = result.get("scores", {})
        for key in ("relevance", "completeness", "accuracy", "clarity", "navigation_quality", "executability"):
            scores.setdefault(key, 0)
        result["scores"] = scores

        # Always recompute overall with fixed weights — ignore the LLM's self-reported
        # value which uses arbitrary weights and can be inconsistent.
        # executability + navigation_quality carry 55% because they measure whether the
        # browser actually reached the right place, which is the hardest thing to get right.
        _WEIGHTS = {
            "executability":      0.30,
            "navigation_quality": 0.25,
            "accuracy":           0.20,
            "completeness":       0.12,
            "relevance":          0.08,
            "clarity":            0.05,
        }
        overall = round(sum(scores.get(k, 0) * w for k, w in _WEIGHTS.items()), 1)
        result["overall"] = overall
        result["pass"] = overall >= config.PASS_THRESHOLD
        result.setdefault("strengths", [])
        result.setdefault("weaknesses", [])
        result.setdefault("reasoning", "")
        return result

    except Exception as exc:
        return {
            "scores": {k: 0 for k in ("relevance", "completeness", "accuracy", "clarity", "navigation_quality", "executability")},
            "overall": 0.0,
            "pass": False,
            "strengths": [],
            "weaknesses": [],
            "reasoning": f"Judge error: {exc}",
            "error": str(exc),
        }
