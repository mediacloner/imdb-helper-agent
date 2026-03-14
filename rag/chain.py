import json
import re
from typing import Any

from graph_client import GraphClient
from ollama_client import chat
from vector_store import VectorStore


_INTENT_PROMPT = """You are an assistant that understands user intent on IMDb.
Given a user question, extract:
1. A keyword for the START page the user is likely on (default: "Ratings, Reviews").
2. A keyword for the END page the user wants to reach.

Use keywords that would appear in an IMDb page title. Examples:
- "Top 250" for the top movies list
- "Most popular" for popular movies
- "Box office" for box office charts
- "Full cast" for cast pages
- "User reviews" for review pages
- "Upcoming releases" for release calendar
- "Genre" for genre browsing

Respond ONLY with a valid JSON object:
{
  "start_state": "<keyword from IMDb page title>",
  "end_state": "<keyword from IMDb page title>"
}
Do not include any explanation outside the JSON object."""

# Used when the graph found a valid path
_ANSWER_WITH_PATH_PROMPT = """You are a helpful assistant guiding users through the IMDb website.

Rules:
- NEVER mention internal IDs like node_id or state_ strings
- Write ONE brief sentence summarising what the user will do
  (e.g. "Search for 'The Matrix' then open its Full Cast page.")
- Do NOT repeat each step — they are shown separately
- Be concise and action-oriented."""

# Used when graph had no path — produces answer + navigation steps in ONE call
_ANSWER_AND_STEPS_PROMPT = """You are a helpful assistant guiding users through the IMDb website.
You have access to IMDb context with URL patterns, movie IDs, and navigation flows.

Your response must be a JSON object with exactly two keys:
- "answer": a concise numbered step-by-step guide for the user (markdown allowed, include real URLs)
- "steps": a JSON array of navigation steps the recorder will execute

Rules for "answer":
- Include real URLs from the context when available
- When cast/actors are requested, ALWAYS include the direct fullcredits URL:
  https://www.imdb.com/title/<tt_id>/fullcredits/ using the known IDs from context
- Be concise and action-oriented

Rules for each step in "steps":
- "description": short human label
- "url": full URL to visit, or "" if not applicable
- "action": object with:
  - "interaction_type": one of "navigate", "search_query", "click", or null
  - "target_element_id": for search_query put the SEARCH TERM (e.g. "The Matrix"),
    for click put a visible label or CSS selector, otherwise null

Example response:
{
  "answer": "1. Search for 'The Matrix'\\n2. Click the movie result\\n3. Open Full Cast at https://www.imdb.com/title/tt0133093/fullcredits/",
  "steps": [
    {"description": "Search for The Matrix", "url": "https://www.imdb.com/find/?q=The+Matrix&s=tt", "action": {"interaction_type": "search_query", "target_element_id": "The Matrix"}},
    {"description": "The Matrix movie page", "url": "https://www.imdb.com/title/tt0133093/", "action": {"interaction_type": "navigate", "target_element_id": null}},
    {"description": "Full cast & crew", "url": "https://www.imdb.com/title/tt0133093/fullcredits/", "action": {"interaction_type": "navigate", "target_element_id": null}}
  ]
}"""


class QueryChain:
    def __init__(self, vector_store: VectorStore, graph_client: GraphClient) -> None:
        self._vector_store = vector_store
        self._graph_client = graph_client

    def run(self, question: str) -> dict[str, Any]:
        # 1. Extract intent (LLM call #1)
        intent_raw = chat(
            [{"role": "system", "content": _INTENT_PROMPT},
             {"role": "user", "content": f"User question: {question}"}],
            response_format="json",
        )
        try:
            intent_raw = re.sub(r"<think>.*?</think>", "", intent_raw, flags=re.DOTALL).strip()
            intent = json.loads(intent_raw)
            start_description = intent.get("start_state", "")
            end_description = intent.get("end_state", "")
        except (json.JSONDecodeError, AttributeError):
            start_description = ""
            end_description = question

        # 2. Query graph for a path
        steps: list[dict[str, Any]] = []
        if start_description and end_description:
            steps = self._graph_client.find_path(start_description, end_description)

        # Detect graph miss
        graph_miss = (
            not steps
            or (
                len(steps) == 1
                and "find" in steps[0].get("node_id", "").lower()
                and steps[0].get("synthetic") is not True
            )
        )

        # 3. Retrieve IMDb context chunks
        rag_chunks = self._vector_store.search(question, k=5)
        context_text = "\n\n".join(c["text"] for c in rag_chunks) if rag_chunks else ""

        if not graph_miss:
            # Graph hit: short summary only (LLM call #2)
            path_text = self._format_path_for_llm(steps)
            answer = chat(
                [{"role": "system", "content": _ANSWER_WITH_PATH_PROMPT},
                 {"role": "user", "content": f"User question: {question}\n\nNavigation path:\n{path_text}"}],
            ).strip()
        else:
            # Graph miss: combined answer + steps in ONE call (LLM call #2)
            combined_raw = chat(
                [{"role": "system", "content": _ANSWER_AND_STEPS_PROMPT},
                 {"role": "user", "content": f"IMDb context:\n{context_text}\n\nUser question: {question}"}],
                response_format="json",
            )
            combined = self._parse_json_object(combined_raw)
            answer = combined.get("answer", "")
            steps = self._build_steps(combined.get("steps", []))

        start_node_id = steps[0].get("node_id", "") if steps else ""
        end_node_id = steps[-1].get("node_id", "") if steps else ""

        return {
            "answer": answer,
            "steps": steps,
            "start_node_id": start_node_id,
            "end_node_id": end_node_id,
            "intent": {
                "start_state": start_description,
                "end_state": end_description,
            },
            "graph_miss": graph_miss,
            "synthetic_steps": graph_miss and len(steps) > 0,
        }

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, AttributeError):
            pass
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict):
                    return parsed
            except (json.JSONDecodeError, AttributeError):
                pass
        return {}

    def _build_steps(self, raw_steps: list) -> list[dict[str, Any]]:
        if not isinstance(raw_steps, list):
            return []
        steps = []
        for i, item in enumerate(raw_steps):
            if not isinstance(item, dict):
                continue
            steps.append({
                "node_id": f"synthetic_{i}",
                "url": item.get("url", ""),
                "description": item.get("description", f"Step {i + 1}"),
                "action": {
                    "interaction_type": (item.get("action") or {}).get("interaction_type"),
                    "target_element_id": (item.get("action") or {}).get("target_element_id"),
                },
                "synthetic": True,
            })
        return steps

    def _format_path_for_llm(self, steps: list[dict[str, Any]]) -> str:
        if not steps:
            return "No navigation path found in the graph for this query."
        lines = []
        for i, step in enumerate(steps):
            description = step.get("description", "Unknown state")
            url = step.get("url", "")
            action = step.get("action", {})
            interaction = (action or {}).get("interaction_type", "")
            element = (action or {}).get("target_element_id", "")
            line = f"Step {i + 1}: {description}"
            if url:
                line += f" ({url})"
            if interaction and element and not element.startswith("state_"):
                line += f" — {interaction} on '{element}'"
            lines.append(line)
        return "\n".join(lines)
