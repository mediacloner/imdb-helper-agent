import json
import os
from typing import Any

from langchain_ollama import ChatOllama
from langchain.schema import HumanMessage, SystemMessage

from graph_client import GraphClient
from vector_store import VectorStore


_INTENT_SYSTEM_PROMPT = """You are an assistant that understands user intent on IMDb.
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

_ANSWER_SYSTEM_PROMPT = """You are a helpful assistant guiding users through the IMDb website.
You have access to IMDb context with URL patterns, movie IDs, and navigation flows.

Rules:
- NEVER mention internal IDs like node_id or strings like "state_chart-moviemeter_12__watchlist_4"
- Only reference page names, visible button/link labels, and real URLs
- When a navigation path IS provided: write ONE brief sentence summarising what
  the user will do (e.g. "Search for 'The Matrix' then open its Full Cast page.").
  Do NOT repeat each step — they are shown separately.
- When NO navigation path is provided: write a full numbered step-by-step answer
  using the IMDb context to include real URLs where possible.
- Be concise and action-oriented."""

_SYNTHETIC_STEPS_PROMPT = """You are a navigation step extractor for IMDb.
Given a step-by-step IMDb answer, extract each navigation action as a JSON array.

Each element must have:
- "description": short human label (e.g. "IMDb Home", "Search results for The Matrix")
- "url": full URL to visit, or "" if no URL for this step
- "action": object with:
    - "interaction_type": one of "navigate", "search_query", "click", or null
    - "target_element_id": for search_query steps put the SEARCH TERM here (e.g. "The Matrix"),
      for click steps put a CSS selector or visible label, otherwise null

Example output:
[
  {"description": "IMDb Home", "url": "https://www.imdb.com", "action": {"interaction_type": "navigate", "target_element_id": null}},
  {"description": "Search for The Matrix", "url": "https://www.imdb.com/find/?q=The+Matrix&s=tt", "action": {"interaction_type": "search_query", "target_element_id": "The Matrix"}},
  {"description": "The Matrix full cast", "url": "https://www.imdb.com/title/tt0133093/fullcredits/", "action": {"interaction_type": "navigate", "target_element_id": null}}
]

Return ONLY a valid JSON array. No explanation outside the array."""


class QueryChain:
    def __init__(self, vector_store: VectorStore, graph_client: GraphClient) -> None:
        self._vector_store = vector_store
        self._graph_client = graph_client
        _base = dict(
            model=os.environ.get("OLLAMA_MODEL", "qwen3:8b"),
            temperature=0,
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"),
        )
        self._llm_json = ChatOllama(**_base, format="json")
        self._llm_text = ChatOllama(**_base)

    def run(self, question: str) -> dict[str, Any]:
        # 1. Extract intent from question
        intent_response = self._llm_json.invoke([
            SystemMessage(content=_INTENT_SYSTEM_PROMPT),
            HumanMessage(content=f"User question: {question}"),
        ])
        try:
            intent = json.loads(intent_response.content.strip())
            start_description = intent.get("start_state", "")
            end_description = intent.get("end_state", "")
        except (json.JSONDecodeError, AttributeError):
            start_description = ""
            end_description = question

        # 2. Query graph for a path
        steps: list[dict[str, Any]] = []
        if start_description and end_description:
            steps = self._graph_client.find_path(start_description, end_description)

        # Detect a graph miss: no steps, or only the generic search fallback
        graph_miss = (
            not steps
            or (
                len(steps) == 1
                and "find" in steps[0].get("node_id", "").lower()
                and steps[0].get("synthetic") is not True
            )
        )

        # 3. Retrieve IMDb context chunks from vector store
        rag_chunks = self._vector_store.search(question, k=5)
        context_text = "\n\n".join(c["text"] for c in rag_chunks) if rag_chunks else ""

        path_text = self._format_path_for_llm([] if graph_miss else steps)

        # 4. Generate the human-readable answer
        answer_response = self._llm_text.invoke([
            SystemMessage(content=_ANSWER_SYSTEM_PROMPT),
            HumanMessage(content=(
                f"IMDb context:\n{context_text}\n\n"
                f"User question: {question}\n\n"
                f"Navigation path found:\n{path_text}"
            )),
        ])
        answer: str = answer_response.content.strip()

        # 5. If graph had no useful path, synthesise steps from the LLM answer
        if graph_miss:
            steps = self._synthesise_steps(answer)

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

    def _synthesise_steps(self, answer_text: str) -> list[dict[str, Any]]:
        """Ask the LLM to parse its own answer into recorder-compatible step dicts."""
        response = self._llm_json.invoke([
            SystemMessage(content=_SYNTHETIC_STEPS_PROMPT),
            HumanMessage(content=answer_text),
        ])
        try:
            raw = json.loads(response.content.strip())
            if not isinstance(raw, list):
                return []
            steps = []
            for i, item in enumerate(raw):
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
        except (json.JSONDecodeError, AttributeError):
            return []

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
