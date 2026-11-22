"""Rebuild the static replay from the exact same engine as the Python API."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from signalbrief.engine import FIXTURES, SCOPES, triage


def case_inputs():
    data = json.loads((FIXTURES / "cases.json").read_text())
    for case in data:
        scope = next(name for name, signals in SCOPES.items() if case["signals"][0] in signals)
        start = datetime(2026, 11, 16, case["hour"], tzinfo=timezone.utc)
        rows = []
        for index, (signal, minute) in enumerate(zip(case["signals"], case["minutes"]), 1):
            t = (start + timedelta(minutes=minute)).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows.append({"id": "E" + case["id"][-3:] + str(index), "time": t, "signal": signal})
        yield case, scope, rows


def payload():
    scenarios = []
    for case, scope, rows in case_inputs():
        result = triage(scope, rows)
        entry = {key: case[key] for key in ("id", "title", "service", "description")}
        scenarios.append(dict(entry, scope=scope, **result))
    return {"version": "1.0.0", "scenarios": scenarios}


if __name__ == "__main__":
    print("Building six synthetic replays")
    (ROOT / "docs/data/scenarios.json").write_text(json.dumps(payload(), indent=2) + "\n")
