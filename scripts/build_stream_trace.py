"""Build a static trace and verify expected event-time decisions against the stream adapter."""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from signalbrief.stream import EventStream


def contract_checks():
    checks = json.loads((ROOT / "fixtures/stream-checks.json").read_text())
    results = []
    start = datetime(2026, 11, 16, 9)
    for check in checks:
        stream = EventStream()
        alerts = []
        for index, (seconds, signal) in enumerate(check["sequence"], 1):
            packet = {"scope": check["scope"], "id": f"E{index:04}",
                      "time": (start + timedelta(seconds=seconds)).isoformat() + "Z", "signal": signal}
            outcome = stream.ingest(packet)
            if outcome["alert"]:
                alerts.append(seconds)
        matches = outcome["priority"] == check["final"] and alerts == check["alert_seconds"]
        if not matches:
            raise ValueError(f"Stream decision changed for {check['name']}")
        results.append({"name": check["name"], "scope": check["scope"], "events": len(check["sequence"]),
                        "expected_priority": check["final"], "observed_priority": outcome["priority"],
                        "expected_alert_seconds": check["alert_seconds"], "observed_alert_seconds": alerts})
    return results


def build():
    source = ROOT / "fixtures/stream-demo.ndjson"
    detector = EventStream()
    records = []
    for line in source.read_text().splitlines():
        packet = json.loads(line)
        records.append({"input": packet, "output": detector.ingest(packet)})
    return {"schema_version": 1, "source": "fixtures/stream-demo.ndjson", "rows": records,
            "contract_checks": contract_checks()}


if __name__ == "__main__":
    path = ROOT / "docs/data/stream-trace.json"
    trace = build()
    path.write_text(json.dumps(trace, indent=2) + "\n")
    print(f"Built {len(trace['rows'])} packet results; verified {len(trace['contract_checks'])} fixture contracts.")
