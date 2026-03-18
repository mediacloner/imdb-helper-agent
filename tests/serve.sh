#!/usr/bin/env bash
# Start the dashboard server — serves tests/ at http://localhost:8765
# Usage: bash tests/serve.sh [port]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${1:-8765}"
URL="http://localhost:$PORT/dashboard/"

echo ""
echo "  🎬  IMDB Helper — Dashboard Server"
echo "  ────────────────────────────────────"
echo "  URL : $URL"
echo "  Stop: Ctrl+C"
echo ""

# Try to open the browser
if command -v xdg-open &>/dev/null; then
  (sleep 1 && xdg-open "$URL") &
elif command -v open &>/dev/null; then
  (sleep 1 && open "$URL") &
fi

cd "$SCRIPT_DIR"
python3 -m http.server "$PORT" --bind 127.0.0.1
