"""Test runner configuration — override via environment variables."""
import os

RAG_URL = os.getenv("RAG_URL", "http://localhost:8000")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
JUDGE_MODEL = os.getenv("JUDGE_MODEL", "qwen3:8b")

# Max concurrent questions sent to the RAG API at once
CONCURRENCY = int(os.getenv("TEST_CONCURRENCY", "1"))

# Seconds before a /query call is abandoned
REQUEST_TIMEOUT = float(os.getenv("TEST_TIMEOUT", "90"))

# Passing threshold (0-10 overall judge score)
PASS_THRESHOLD = float(os.getenv("PASS_THRESHOLD", "6.0"))

# Whether to call /record and generate a video for each question (very slow)
RECORD_VIDEO = os.getenv("RECORD_VIDEO", "false").lower() == "true"

RESULTS_DIR = os.getenv("RESULTS_DIR", os.path.join(os.path.dirname(__file__), "results"))
