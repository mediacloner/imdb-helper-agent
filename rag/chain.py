import json
import os
from typing import Any

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from graph_client import GraphClient
from vector_store import VectorStore


_INTENT_SYSTEM_PROMPT = """You are an assistant that understands user intent on a website.
Given a user question and relevant documentation excerpts, extract:
1. A short description of the START UI state the user is likely at (e.g., "home page", "film detail page").
2. A short description of the END UI state the user wants to reach (e.g., "full cast list page", "user ratings page").

Respond ONLY with a valid JSON object with two keys:
{
  "start_state": "<short description of the starting UI state>",
  "end_state": "<short description of the desired ending UI state>"
}
Do not include any explanation outside the JSON object."""

_ANSWER_SYSTEM_PROMPT = """You are a helpful assistant that guides users through a website step by step.
Given:
- The user's question
- Relevant documentation excerpts
- A list of UI states and transitions forming a navigation path

Write a clear, numbered, step-by-step answer in plain English explaining how the user can accomplish their goal.
Be concise and action-oriented. Reference specific button names, links, or page names where available."""


class QueryChain:
    def __init__(self, vector_store: VectorStore, graph_client: GraphClient) -> None:
        self._vector_store = vector_store
        self._graph_client = graph_client
        self._llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=os.environ["OPENAI_API_KEY"],
        )

    def run(self, question: str) -> dict[str, Any]:
        """Process a user question and return a structured answer with navigation steps.

        Steps:
        1. Retrieve relevant manual context from the vector store.
        2. Use the LLM to extract the user's intent (start and end UI states).
        3. Query the Neo4j graph for a path between those states.
        4. Use the LLM to generate a human-readable answer from the context and path.
        5. Return answer and steps.
        """
        context_chunks: list[dict[str, Any]] = self._vector_store.search(question, k=5)
        context_text: str = "\n\n".join(
            f"[Source: {chunk['metadata'].get('filename', 'unknown')}]\n{chunk['text']}"
            for chunk in context_chunks
        )

        intent_messages = [
            SystemMessage(content=_INTENT_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"User question: {question}\n\n"
                    f"Documentation context:\n{context_text}"
                )
            ),
        ]
        intent_response = self._llm.invoke(intent_messages)
        intent_text: str = intent_response.content.strip()

        try:
            intent: dict[str, str] = json.loads(intent_text)
            start_description: str = intent.get("start_state", "")
            end_description: str = intent.get("end_state", "")
        except (json.JSONDecodeError, AttributeError):
            start_description = ""
            end_description = question

        steps: list[dict[str, Any]] = []
        start_node_id: str = ""
        end_node_id: str = ""

        if start_description and end_description:
            steps = self._graph_client.find_path(start_description, end_description)

        if steps:
            start_node_id = steps[0].get("node_id", "")
            end_node_id = steps[-1].get("node_id", "")

        path_text: str = self._format_path_for_llm(steps)

        answer_messages = [
            SystemMessage(content=_ANSWER_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"User question: {question}\n\n"
                    f"Documentation context:\n{context_text}\n\n"
                    f"Navigation path found:\n{path_text}"
                )
            ),
        ]
        answer_response = self._llm.invoke(answer_messages)
        answer: str = answer_response.content.strip()

        return {
            "answer": answer,
            "steps": steps,
            "start_node_id": start_node_id,
            "end_node_id": end_node_id,
        }

    def _format_path_for_llm(self, steps: list[dict[str, Any]]) -> str:
        """Convert a list of path steps into a human-readable text block."""
        if not steps:
            return "No navigation path found in the graph for this query."

        lines: list[str] = []
        for i, step in enumerate(steps):
            description = step.get("description", "Unknown state")
            url = step.get("url", "")
            action = step.get("action", {})
            interaction = action.get("interaction_type", "")
            element = action.get("target_element_id", "")

            line = f"Step {i + 1}: {description}"
            if url:
                line += f" ({url})"
            if interaction and element:
                line += f" — Action: {interaction} on '{element}'"
            lines.append(line)

        return "\n".join(lines)
