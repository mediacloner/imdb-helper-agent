#!/usr/bin/env bash
# IMDB Helper — Interactive Test Menu
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."
cd "$ROOT"

RAG_URL="${RAG_URL:-http://localhost:8000}"
VENV="$SCRIPT_DIR/.venv"

# ── colours ───────────────────────────────────────────────────────────────────
BOLD='\033[1m'; YELLOW='\033[0;33m'; GREEN='\033[0;32m'
RED='\033[0;31m'; CYAN='\033[0;36m'; MUTED='\033[0;90m'; RESET='\033[0m'

hr()   { echo -e "${MUTED}────────────────────────────────────────────────────${RESET}"; }
title(){ clear; echo -e "\n  ${YELLOW}${BOLD}🎬  IMDB Helper — Test Runner${RESET}\n"; hr; }
ok()   { echo -e "  ${GREEN}✓ $*${RESET}"; }
err()  { echo -e "  ${RED}✗ $*${RESET}"; }
info() { echo -e "  ${MUTED}→ $*${RESET}"; }

# ── setup venv ────────────────────────────────────────────────────────────────
setup_venv() {
  if [ ! -f "$VENV/bin/python" ]; then
    info "Creating virtualenv at tests/.venv ..."
    python3 -m venv "$VENV"
  fi
  if ! "$VENV/bin/python" -c "import httpx" 2>/dev/null; then
    info "Installing httpx..."
    "$VENV/bin/pip" install httpx --quiet
  fi
}

# ── check API ─────────────────────────────────────────────────────────────────
check_api() {
  if curl -sf "$RAG_URL/health" > /dev/null 2>&1; then
    ok "RAG API ready at $RAG_URL"
  else
    err "RAG API not reachable at $RAG_URL"
    info "Start the stack first:  bash scripts/run.sh  → option 6"
    exit 1
  fi
}

# ── read a number in range from /dev/tty ──────────────────────────────────────
read_number() {
  # $1=prompt  $2=min  $3=max  $4=default(optional)
  local prompt="$1" min="$2" max="$3" default="${4:-}"
  local hint="$min-$max"
  [ -n "$default" ] && hint="$min-$max, Enter=$default"
  while true; do
    printf "  ${CYAN}%s [%s]: ${RESET}" "$prompt" "$hint" >/dev/tty
    read -r val </dev/tty
    [ -z "$val" ] && val="$default"
    if [[ "$val" =~ ^[0-9]+$ ]] && [ "$val" -ge "$min" ] && [ "$val" -le "$max" ]; then
      echo "$val"; return
    fi
    printf "  ${RED}✗ Enter a number between %s and %s${RESET}\n" "$min" "$max" >/dev/tty
  done
}

# ── yes/no from /dev/tty ──────────────────────────────────────────────────────
read_yn() {
  local prompt="$1" default="${2:-n}"
  while true; do
    printf "  ${CYAN}%s [y/n, Enter=%s]: ${RESET}" "$prompt" "$default" >/dev/tty
    read -r val </dev/tty
    val="${val:-$default}"
    case "$val" in
      y|Y) echo "y"; return ;;
      n|N) echo "n"; return ;;
      *) printf "  ${RED}✗ Enter y or n${RESET}\n" >/dev/tty ;;
    esac
  done
}

# ─────────────────────────────────────────────────────────────────────────────
title
echo -e "  Benchmark the IMDB Helper RAG system across 200 questions.\n"
hr
echo ""
info "API: $RAG_URL"
check_api
setup_venv

# ── count questions per category/difficulty from questions.json ───────────────
Q_FILE="$SCRIPT_DIR/questions.json"
count_q() {
  # $1 = field (category|difficulty), $2 = value (or "all")
  if [ "$2" = "all" ]; then
    python3 -c "import json; d=json.load(open('$Q_FILE')); print(len(d))"
  else
    python3 -c "import json; d=json.load(open('$Q_FILE')); print(sum(1 for q in d if q['$1']=='$2'))"
  fi
}

N_ALL=$(count_q category all)
N_BASIC_NAV=$(count_q category basic_navigation)
N_CAST=$(count_q category cast_and_crew)
N_MOVIE=$(count_q category movie_details)
N_TV=$(count_q category tv_shows_episodes)
N_CHARTS=$(count_q category charts_rankings)
N_SEARCH=$(count_q category advanced_search)
N_USER=$(count_q category user_features)
N_COMPLEX=$(count_q category complex_tasks)
N_D_BASIC=$(count_q difficulty basic)
N_D_INTER=$(count_q difficulty intermediate)
N_D_ADV=$(count_q difficulty advanced)
N_D_EXP=$(count_q difficulty expert)

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1 — What questions to run?
# Single flat list: 0=all, 1-8=by topic, 9-12=by difficulty
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo -e "  ${BOLD}Step 1 — Which questions do you want to run?${RESET}"
echo ""
printf "  ${MUTED}  #    Questions${RESET}\n"
echo ""
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n"  0  "($N_ALL)"  "All questions"
echo ""
printf "  ${MUTED}  ─── By topic ───────────────────────────────────────────${RESET}\n"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n"  1  "($N_BASIC_NAV)"  "Basic Navigation       — search, homepage, trailers, runtime"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n"  2  "($N_CAST)"       "Cast & Crew            — actors, directors, bio, filmography"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n"  3  "($N_MOVIE)"      "Movie Details          — trivia, goofs, box office, quotes"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n"  4  "($N_TV)"         "TV Shows & Episodes    — seasons, episode guide, air dates"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n"  5  "($N_CHARTS)"     "Charts & Rankings      — Top 250, STARmeter, Box Office"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n"  6  "($N_SEARCH)"     "Advanced Search        — year, country, language, genre filters"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n"  7  "($N_USER)"       "User Features          — watchlist, ratings, reviews, lists"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n"  8  "($N_COMPLEX)"    "Complex Tasks          — multi-filter, franchises, award combos"
echo ""
printf "  ${MUTED}  ─── By difficulty ──────────────────────────────────────${RESET}\n"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n"  9  "($N_D_BASIC)"  "Basic        — most fundamental actions only"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n" 10  "($N_D_INTER)"  "Intermediate — cast, details, charts, TV episodes"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n" 11  "($N_D_ADV)"    "Advanced     — search filters, user features"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n" 12  "($N_D_EXP)"    "Expert       — multi-step, complex queries"
echo ""
printf "  ${MUTED}  ─── Custom ─────────────────────────────────────────────${RESET}\n"
printf "  ${YELLOW}%3d${RESET}.  %-12s  %s\n" 13  ""       "Enter specific question IDs (e.g. 91, 92, 111)"
echo ""

sel=$(read_number "Choose" 0 13)

FILTER_CAT=""
FILTER_DIFF=""
FILTER_IDS=""

case "$sel" in
  0)  ;;  # all
  1)  FILTER_CAT="basic_navigation" ;;
  2)  FILTER_CAT="cast_and_crew" ;;
  3)  FILTER_CAT="movie_details" ;;
  4)  FILTER_CAT="tv_shows_episodes" ;;
  5)  FILTER_CAT="charts_rankings" ;;
  6)  FILTER_CAT="advanced_search" ;;
  7)  FILTER_CAT="user_features" ;;
  8)  FILTER_CAT="complex_tasks" ;;
  9)  FILTER_DIFF="basic" ;;
  10) FILTER_DIFF="intermediate" ;;
  11) FILTER_DIFF="advanced" ;;
  12) FILTER_DIFF="expert" ;;
  13)
    printf "\n  ${CYAN}Enter question IDs (comma-separated, e.g. 1,91,111): ${RESET}" >/dev/tty
    read -r FILTER_IDS </dev/tty
    ;;
esac

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2 — How many?  (skipped if specific IDs chosen)
# ═══════════════════════════════════════════════════════════════════════════════
LIMIT_ARG=""
START_ID=""

if [ -z "$FILTER_IDS" ]; then
  echo ""
  hr
  echo -e "  ${BOLD}Step 2 — How many questions?${RESET}"
  echo ""
  printf "  ${YELLOW}  1${RESET}.  All available in selection\n"
  printf "  ${YELLOW}  2${RESET}.  First N questions\n"
  printf "  ${YELLOW}  3${RESET}.  Starting from question ID\n"
  echo ""
  range_sel=$(read_number "Choose" 1 3)

  case "$range_sel" in
    2)
      lim=$(read_number "How many questions" 1 200 20)
      LIMIT_ARG="--limit $lim"
      ;;
    3)
      START_ID=$(read_number "Start from question ID" 1 200 1)
      ;;
  esac
fi

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3 — AI Judge
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
hr
echo -e "  ${BOLD}Step 3 — AI Judge${RESET}"
info "Evaluates each answer on 6 dimensions using Ollama (~10s per question extra)"
use_judge=$(read_yn "Enable AI Judge?" "y")

# ═══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Video
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
hr
echo -e "  ${BOLD}Step 4 — Video recording${RESET}"
info "Recorded by default so the AI judge can evaluate real Playwright execution"
info "Each video takes ~30-60s — skip to run much faster (steps still logged)"
skip_video=$(read_yn "Skip video recording?" "n")

# ═══════════════════════════════════════════════════════════════════════════════
# Summary + confirm
# ═══════════════════════════════════════════════════════════════════════════════
title
echo -e "  ${BOLD}Ready to run${RESET}\n"
hr
echo ""

FILTER_LABEL="All 200 questions"
[ -n "$FILTER_CAT"  ] && FILTER_LABEL="Category: $FILTER_CAT"
[ -n "$FILTER_DIFF" ] && FILTER_LABEL="Difficulty: $FILTER_DIFF"
[ -n "$FILTER_IDS"  ] && FILTER_LABEL="IDs: $FILTER_IDS"

printf "  %-22s %s\n" "Questions:"     "$FILTER_LABEL"
printf "  %-22s %s\n" "Limit:"         "${LIMIT_ARG:-(all in selection)}"
printf "  %-22s %s\n" "Start from ID:" "${START_ID:-1}"
printf "  %-22s %s\n" "AI Judge:"      "$([ "$use_judge" = "y" ] && echo "ON  (6-dimension scoring)" || echo "OFF")"
printf "  %-22s %s\n" "Video:"         "$([ "$skip_video" = "y" ] && echo "OFF (playback script logged)" || echo "ON  (recorded for judge)")"
printf "  %-22s %s\n" "API:"           "$RAG_URL"
echo ""
hr
echo ""

confirm=$(read_yn "Start?" "y")
[ "$confirm" = "n" ] && { info "Cancelled."; exit 0; }

# ── Build args ────────────────────────────────────────────────────────────────
ARGS=()
[ -n "$FILTER_CAT"  ] && ARGS+=("--category"   "$FILTER_CAT")
[ -n "$FILTER_DIFF" ] && ARGS+=("--difficulty"  "$FILTER_DIFF")
[ -n "$FILTER_IDS"  ] && ARGS+=("--ids"         "$FILTER_IDS")
[ -n "$LIMIT_ARG"   ] && ARGS+=($LIMIT_ARG)
[ "$use_judge"   = "n" ] && ARGS+=("--no-judge")
[ "$skip_video"  = "y" ] && ARGS+=("--no-video")

[ -n "$START_ID" ] && export TEST_START_ID="$START_ID"

echo ""
echo -e "  ${CYAN}python runner.py ${ARGS[*]:-}${RESET}"
echo ""
hr
echo ""

RAG_URL="$RAG_URL" "$VENV/bin/python" "$SCRIPT_DIR/runner.py" "${ARGS[@]+"${ARGS[@]}"}"

# ── Post-run ──────────────────────────────────────────────────────────────────
LATEST_DIR=$(ls -td "$SCRIPT_DIR/results"/[0-9]* 2>/dev/null | head -1 || true)
if [ -n "$LATEST_DIR" ]; then
  echo ""
  hr
  ok "Results: $LATEST_DIR"
  ok "Dashboard: $SCRIPT_DIR/dashboard/index.html"
  echo ""
  info "Load $(basename "$LATEST_DIR")/summary.json in the dashboard"
  echo ""
  if command -v xdg-open &>/dev/null; then
    open_dash=$(read_yn "Open dashboard in browser?" "y")
    [ "$open_dash" = "y" ] && xdg-open "$SCRIPT_DIR/dashboard/index.html" 2>/dev/null &
  fi
fi
