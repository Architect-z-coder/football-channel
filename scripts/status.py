"""Write data/dashboard/status.json so the dashboard can show what the pipeline is doing.

Usage (inside GitHub Actions): python scripts/status.py running|done|failed
Reads REQ_ID, MODE, MATCH and RUN_URL from the environment.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "data" / "dashboard" / "status.json"
REASON = ROOT / "out" / "stop_reason.txt"


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> None:
    state = sys.argv[1]
    old = {}
    if STATUS.exists():
        try:
            old = json.loads(STATUS.read_text(encoding="utf-8"))
        except ValueError:
            old = {}
    st = {
        "request_id": os.environ.get("REQ_ID", ""),
        "mode": os.environ.get("MODE", ""),
        "match": os.environ.get("MATCH", ""),
        "trigger": os.environ.get("TRIGGER", ""),
        "state": state,
        "run_url": os.environ.get("RUN_URL", ""),
        "started": old.get("started") if state != "running" else now(),
        "finished": now() if state != "running" else None,
        "reason": None,
    }
    if state == "failed":
        st["reason"] = (REASON.read_text(encoding="utf-8")[:1500] if REASON.exists()
                        else "The run stopped with an error. Open the run log for details.")
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    STATUS.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
