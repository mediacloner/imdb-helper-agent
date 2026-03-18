#!/usr/bin/env bash
# View and format RAG request logs in a human-readable format
# Usage: bash scripts/logs.sh [--tail N] [--event query|record_success|record_failed]

set -euo pipefail

TAIL=0
FILTER_EVENT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tail) TAIL="$2"; shift 2 ;;
    --event) FILTER_EVENT="$2"; shift 2 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

docker exec -i imdbhelper-rag-1 python3 - <<PYEOF
import json, sys, os, textwrap

log_path = "/app/logs/requests.log"
if not os.path.exists(log_path):
    print("No log file found at", log_path)
    sys.exit(0)

with open(log_path) as f:
    lines = [l.strip() for l in f if l.strip()]

tail = $TAIL
filter_event = "$FILTER_EVENT"

if filter_event:
    lines = [l for l in lines if ('"event": "' + filter_event + '"') in l]

if tail > 0:
    lines = lines[-tail:]

W = 72
SEP_HEAVY = "═" * W
SEP_LIGHT = "─" * W

def dur(ms):
    if ms is None:
        return ""
    if ms < 1000:
        return f"  ({ms} ms)"
    return f"  ({ms/1000:.1f} s)"

def wrap(text, indent=18):
    pad = " " * indent
    return textwrap.fill(text, width=W, initial_indent=pad, subsequent_indent=pad).lstrip()

def clean_target(t):
    if not t:
        return ""
    if "__" in t or t.startswith("state_"):
        return ""
    return t

for line in lines:
    try:
        e = json.loads(line)
    except Exception:
        print(line)
        continue

    ts    = e.get("timestamp", "")[:19].replace("T", " ")
    event = e.get("event", "unknown").upper()
    ms    = e.get("duration_ms")

    print()
    print(SEP_HEAVY)

    if event == "QUERY":
        print(f"  QUERY{dur(ms)}  [{ts}]")
        print(SEP_LIGHT)
        q = e.get("question", "")
        print(f"  {'Question':14s}  {q}")

        intent = e.get("llm_intent") or {}
        if intent:
            print(f"  {'Intent':14s}  {intent.get('start_state','')}  →  {intent.get('end_state','')}")

        graph_miss = e.get("graph_miss")
        if graph_miss is not None:
            hit = "MISS ✗" if graph_miss else "HIT  ✓"
            print(f"  {'Graph':14s}  {hit}")

        steps_count = e.get("steps_count", len(e.get("steps", [])))
        synthetic   = e.get("synthetic_steps", False)
        slabel      = "  (synthetic)" if synthetic else ""
        print(f"  {'Steps':14s}  {steps_count}{slabel}")

        for i, s in enumerate(e.get("steps", []), 1):
            desc   = s.get("description", "")
            url    = s.get("url", "")
            act    = s.get("action") or {}
            itype  = act.get("interaction_type") or ""
            target = clean_target(act.get("target_element_id") or "")
            badge  = f"[{itype}]" if itype else ""
            tpart  = f" → {target}" if target else ""
            print(f"  {'':14s}  {i}.  {desc}  {badge}{tpart}")
            if url:
                print(f"  {'':14s}       {url}")

        answer = e.get("answer", "")
        if answer:
            print(SEP_LIGHT)
            print(f"  {'Answer':14s}  {wrap(answer)}")

    elif event in ("RECORD_SUCCESS", "RECORD_FAILED"):
        icon = "✓" if event == "RECORD_SUCCESS" else "✗"
        print(f"  RECORD {icon}{dur(ms)}  [{ts}]")
        print(SEP_LIGHT)
        video = e.get("video_url", "")
        err   = e.get("error", "")
        if video:
            print(f"  {'Video':14s}  {video}")
        if err:
            print(f"  {'Error':14s}  {err}")
        steps = e.get("steps", [])
        print(f"  {'Steps':14s}  {len(steps)}")
        for i, s in enumerate(steps, 1):
            desc   = s.get("description", "")
            url    = s.get("url", "")
            act    = s.get("action") or {}
            itype  = act.get("interaction_type") or ""
            target = clean_target(act.get("target_element_id") or "")
            badge  = f"[{itype}]" if itype else ""
            tpart  = f" → {target}" if target else ""
            print(f"  {'':14s}  {i}.  {desc}  {badge}{tpart}")
            if url:
                print(f"  {'':14s}       {url}")

    elif event == "RECORD_COOKIE":
        dismissed = e.get("dismissed", False)
        icon = "✓" if dismissed else "✗"
        sel = e.get("selector", "—")
        print(f"  COOKIE {icon}  [{ts}]")
        print(SEP_LIGHT)
        if dismissed:
            print(f"  {'Selector':14s}  {sel}")
        else:
            print(f"  {'Result':14s}  banner not found")

    elif event in ("RECORD_STEP", "RECORD_STEP_START"):
        label = "STEP>" if event == "RECORD_STEP_START" else "STEP "
        print(f"  {label}{dur(ms)}  [{ts}]")
        print(SEP_LIGHT)
        print(f"  {'#':14s}  {e.get('step', '?')}  {e.get('description', '')}")
        if event == "RECORD_STEP_START":
            print(f"  {'interaction':14s}  {e.get('interaction', '')}  →  {e.get('target', '') or '(url only)'}")
            if e.get("url"):
                print(f"  {'url':14s}  {e.get('url')}")
        else:
            ok = "✓" if e.get("success") else "✗"
            print(f"  {'method':14s}  {e.get('method', '')}  {ok}")

    else:
        print(f"  {event}{dur(ms)}  [{ts}]")
        print(SEP_LIGHT)
        for k, v in e.items():
            if k not in ("timestamp", "event", "duration_ms"):
                print(f"  {k:<16}  {v}")

print()
print(SEP_HEAVY)
print()
PYEOF
