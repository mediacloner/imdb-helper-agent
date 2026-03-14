import json
import os
from datetime import datetime, timezone
from typing import Any

LOGS_DIR = "/app/logs"
LOG_FILE = os.path.join(LOGS_DIR, "requests.log")


def log_entry(event: str, data: dict[str, Any]) -> None:
    """Append a JSON log entry to the request log file."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **data,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
