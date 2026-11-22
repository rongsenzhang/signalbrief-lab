"""Build the integration lab's exact input/output pairs from the Python API."""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from signalbrief.api import parse_body


def examples():
    start = datetime(2026, 11, 16, 9, 0)
    records = {}
    for report in ("owner_disputes", "owner_confirms"):
        for minutes in (1, 5, 15, 16, 30):
            later = start + timedelta(minutes=minutes)
            request = {"schema_version": "1", "scope": "ACCESS-A", "events": [
                {"id": "E5001", "time": start.strftime("%Y-%m-%dT%H:%M:%SZ"), "signal": "session_opened"},
                {"id": "E5002", "time": later.strftime("%Y-%m-%dT%H:%M:%SZ"), "signal": report},
            ]}
            response = parse_body(json.dumps(request).encode())
            records[f"{report}-{minutes}"] = {"request": request, "response": response}
    return records


if __name__ == "__main__":
    path = ROOT / "docs/data/contract-examples.json"
    records = examples()
    path.write_text(json.dumps(records, separators=(",", ":")) + "\n")
    print(f"Built {len(records)} API examples.")
