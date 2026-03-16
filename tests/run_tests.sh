#!/usr/bin/env bash
# IMDB Helper — quick-start test runner
# Usage:
#   bash tests/run_tests.sh                  # all 200 questions, no video
#   bash tests/run_tests.sh --limit 20       # first 20 only (smoke test)
#   bash tests/run_tests.sh --category basic_navigation
#   bash tests/run_tests.sh --difficulty expert
#   bash tests/run_tests.sh --ids 91,92,93   # specific questions
#   bash tests/run_tests.sh --record-video   # generate videos (very slow)
#   bash tests/run_tests.sh --no-judge       # skip AI judge (speed run)
#   RAG_URL=http://localhost:8000 bash tests/run_tests.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
cd "$ROOT"

RAG_URL="${RAG_URL:-http://localhost:8000}"

echo "Checking RAG API health at $RAG_URL ..."
if ! curl -sf "$RAG_URL/health" > /dev/null 2>&1; then
  echo "ERROR: RAG API not reachable at $RAG_URL"
  echo "Start the stack first:  bash scripts/run.sh  → option 6"
  exit 1
fi
echo "API is up."
echo ""

# Check Python dependencies — use a venv to avoid system-package restrictions
VENV="$ROOT/tests/.venv"
if [ ! -f "$VENV/bin/python" ]; then
  echo "Creating test virtualenv at tests/.venv ..."
  python3 -m venv "$VENV"
fi
if ! "$VENV/bin/python" -c "import httpx" 2>/dev/null; then
  echo "Installing test dependencies..."
  "$VENV/bin/pip" install httpx --quiet
fi

RAG_URL="$RAG_URL" "$VENV/bin/python" "$SCRIPT_DIR/runner.py" "$@"
