import json
import os
from datetime import datetime, timezone

LOG_FILE = "audit_log.json"


def _load_log():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save_log(entries):
    with open(LOG_FILE, "w") as f:
        json.dump(entries, f, indent=2)


def log_submission(entry):
    entries = _load_log()
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    entries.append(entry)
    _save_log(entries)


def log_appeal(content_id, creator_reasoning):
    entries = _load_log()
    found = False
    for entry in entries:
        if entry.get("content_id") == content_id and entry.get("type") == "submission":
            entry["status"] = "under_review"
            entry["appeal_reasoning"] = creator_reasoning
            entry["appeal_timestamp"] = datetime.now(timezone.utc).isoformat()
            found = True
            break
    if not found:
        return None
    _save_log(entries)
    return content_id


def get_log():
    return _load_log()
