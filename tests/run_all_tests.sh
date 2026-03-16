#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# IMDB Helper — Full Test Suite
# Starts the production stack if needed, runs all 200 questions,
# evaluates with the AI judge, and opens the dashboard.
#
# Usage:
#   bash tests/run_all_tests.sh               # full run, all 200 questions
#   bash tests/run_all_tests.sh --limit 20    # smoke test (first 20)
#   bash tests/run_all_tests.sh --no-judge    # skip AI judge (faster)
#   bash tests/run_all_tests.sh --no-docker   # assume stack already running
#   bash tests/run_all_tests.sh --category advanced_search
#   bash tests/run_all_tests.sh --difficulty expert
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

# ── resolve project root ──────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
cd "$ROOT"

RAG_URL="${RAG_URL:-http://localhost:8000}"
START_DOCKER=true
RUNNER_ARGS=()

# ── parse our own flags; pass the rest to runner.py ──────────────────────────
for arg in "$@"; do
  case "$arg" in
    --no-docker) START_DOCKER=false ;;
    *) RUNNER_ARGS+=("$arg") ;;
  esac
done

# ── colours ───────────────────────────────────────────────────────────────────
BOLD='\033[1m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
RESET='\033[0m'

banner() { echo -e "\n${YELLOW}${BOLD}▶ $*${RESET}"; }
ok()     { echo -e "  ${GREEN}✓ $*${RESET}"; }
err()    { echo -e "  ${RED}✗ $*${RESET}"; }
info()   { echo -e "  ${CYAN}→ $*${RESET}"; }

# ─────────────────────────────────────────────────────────────────────────────
banner "IMDB Helper — Test Suite"
echo -e "  API: ${CYAN}$RAG_URL${RESET}   Questions: ${BOLD}200${RESET}"
echo ""

# ── 1. Python deps ────────────────────────────────────────────────────────────
banner "Checking Python dependencies"
VENV="$SCRIPT_DIR/.venv"
if [ ! -f "$VENV/bin/python" ]; then
  info "Creating test virtualenv at tests/.venv ..."
  python3 -m venv "$VENV"
fi
if ! "$VENV/bin/python" -c "import httpx" 2>/dev/null; then
  info "Installing httpx into venv..."
  "$VENV/bin/pip" install httpx --quiet
fi
ok "httpx available (tests/.venv)"

# ── 2. Optionally start Docker stack ─────────────────────────────────────────
if [ "$START_DOCKER" = true ]; then
  banner "Starting production stack"

  if ! command -v docker &>/dev/null; then
    err "docker not found — start the stack manually and re-run with --no-docker"
    exit 1
  fi

  # Check if neo4j + rag are already up
  RAG_RUNNING=$(docker compose ps --status running --services 2>/dev/null | grep -c "rag" || true)

  if [ "$RAG_RUNNING" -ge 1 ]; then
    ok "Stack already running"
  else
    info "Running: docker compose --profile production up --build -d"
    docker compose --profile production up --build -d
    ok "Stack started"
  fi
fi

# ── 3. Wait for RAG API ───────────────────────────────────────────────────────
banner "Waiting for RAG API to be ready"
MAX_WAIT=120
WAITED=0
INTERVAL=5

while true; do
  if curl -sf "$RAG_URL/health" > /dev/null 2>&1; then
    ok "RAG API is ready at $RAG_URL"
    break
  fi
  if [ "$WAITED" -ge "$MAX_WAIT" ]; then
    err "RAG API did not become ready after ${MAX_WAIT}s"
    echo ""
    echo "  Troubleshoot:"
    echo "    docker compose logs rag --tail 40"
    echo "    docker compose ps"
    exit 1
  fi
  info "Not ready yet (${WAITED}s elapsed) — retrying in ${INTERVAL}s..."
  sleep "$INTERVAL"
  WAITED=$((WAITED + INTERVAL))
done

# ── 4. Check Ollama (for the AI judge) ───────────────────────────────────────
banner "Checking Ollama (AI judge)"
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
if curl -sf "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
  ok "Ollama reachable at $OLLAMA_URL"
else
  echo -e "  ${YELLOW}⚠  Ollama not reachable at $OLLAMA_URL${RESET}"
  info "AI judge scores will fail — adding --no-judge automatically"
  RUNNER_ARGS+=("--no-judge")
fi

# ── 5. Run the test suite ─────────────────────────────────────────────────────
banner "Running test suite (${#RUNNER_ARGS[@]} extra args: ${RUNNER_ARGS[*]:-none})"
echo ""

RAG_URL="$RAG_URL" OLLAMA_BASE_URL="$OLLAMA_URL" \
  "$VENV/bin/python" tests/runner.py "${RUNNER_ARGS[@]+"${RUNNER_ARGS[@]}"}"

# ── 6. Find the latest results dir ───────────────────────────────────────────
LATEST_DIR=$(ls -td "$SCRIPT_DIR/results"/[0-9]* 2>/dev/null | head -1 || true)

if [ -n "$LATEST_DIR" ]; then
  SUMMARY="$LATEST_DIR/summary.json"
  RESULTS="$LATEST_DIR/results.jsonl"
  DASHBOARD="$SCRIPT_DIR/dashboard/index.html"

  echo ""
  banner "Results"
  ok "Summary : $SUMMARY"
  ok "Details : $RESULTS"
  echo ""
  echo -e "  ${BOLD}Open the dashboard:${RESET}"
  echo -e "  ${CYAN}xdg-open \"$DASHBOARD\"${RESET}   (Linux)"
  echo -e "  ${CYAN}open \"$DASHBOARD\"${RESET}        (macOS)"
  echo ""
  echo -e "  Then load: ${YELLOW}$SUMMARY${RESET}"
  echo ""

  # Try to open automatically
  if command -v xdg-open &>/dev/null; then
    xdg-open "$DASHBOARD" 2>/dev/null &
    ok "Dashboard opened in browser"
  elif command -v open &>/dev/null; then
    open "$DASHBOARD" 2>/dev/null &
    ok "Dashboard opened in browser"
  fi
fi
