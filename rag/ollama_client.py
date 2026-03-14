"""
Thin synchronous wrapper around the Ollama /api/chat endpoint.
Passes think=false so qwen3 skips its reasoning phase (~5s instead of ~30s per call).
"""
import json
import os
from typing import Any

import httpx


_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
_TIMEOUT = 120


def chat(messages: list[dict[str, str]], response_format: str | None = None) -> str:
    """
    Call Ollama chat API and return the assistant message content.

    Args:
        messages: list of {"role": "system"|"user"|"assistant", "content": "..."}
        response_format: if "json", asks the model to return valid JSON
    """
    payload: dict[str, Any] = {
        "model": _MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
    }
    if response_format == "json":
        payload["format"] = "json"

    response = httpx.post(
        f"{_BASE_URL}/api/chat",
        json=payload,
        timeout=_TIMEOUT,
    )
    response.raise_for_status()
    data = response.json()
    return data["message"]["content"]
