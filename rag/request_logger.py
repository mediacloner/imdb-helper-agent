import json
import os
import time
from datetime import datetime, timezone
from typing import Any

LOGS_DIR = "/app/logs"
LOG_FILE = os.path.join(LOGS_DIR, "requests.log")


def log_entry(event: str, data: dict[str, Any], duration_ms: int | None = None) -> None:
    """Append a JSON log entry to the request log file."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    entry: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    if duration_ms is not None:
        entry["duration_ms"] = duration_ms
    entry.update(data)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def now_ms() -> int:
    """Return current time in milliseconds."""
    return int(time.monotonic() * 1000)
