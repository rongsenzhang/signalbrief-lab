"""Measure per-packet Python decision time over a full synthetic stream session."""
import argparse
import json
import platform
import sys
from datetime import datetime, timedelta
from math import ceil
from pathlib import Path
from time import perf_counter_ns

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from signalbrief.stream import EventStream

PATTERNS = {
    "ACCESS-A": ("access_declined", "session_opened", "owner_disputes", "owner_confirms"),
    "DEVICE-A": ("endpoint_block", "endpoint_note", "process_observed"),
    "BACKUP-A": ("backup_late", "restore_pending", "restore_verified"),
    "FEED-A": ("monitor_gap", "vague_notice", "feed_resumed"),
}


def benchmark():
    packets = []
    first = datetime(2026, 11, 16, 9)
    for i in range(10000):
        timestamp = (first + timedelta(seconds=i)).isoformat() + "Z"
        for scope, pattern in PATTERNS.items():
            packets.append({"scope": scope, "time": timestamp, "id": f"E{i:04}",
                            "signal": pattern[i % len(pattern)]})
    stream = EventStream()
    nanos = []
    alerts = 0
    start = perf_counter_ns()
    for packet in packets:
        received = perf_counter_ns()
        result = stream.ingest(packet)
        nanos.append(perf_counter_ns() - received)
        if result["status"] != "accepted":
            raise RuntimeError("Unique valid workload should always be accepted.")
        alerts += int(result["alert"])
    seconds = (perf_counter_ns() - start) / 1_000_000_000
    nanos.sort()
    return {
        "packets": len(packets), "scopes": len(PATTERNS), "unique_ids_per_scope": 10000,
        "alerts": alerts, "seconds": round(seconds, 4), "packets_per_second": round(len(packets) / seconds),
        "decision_p50_us": round(nanos[ceil(len(nanos) * .50) - 1] / 1000, 3),
        "decision_p95_us": round(nanos[ceil(len(nanos) * .95) - 1] / 1000, 3),
        "decision_p99_us": round(nanos[ceil(len(nanos) * .99) - 1] / 1000, 3),
        "machine": platform.machine(), "system": platform.system(), "python": platform.python_version(),
        "method": "One local sequential caller, four interleaved fictional subjects, 10,000 unique IDs each. "
                  "A fresh in-memory detector processes prebuilt normalised dictionaries. Individual timers cover ingest(). "
                  "The throughput timer includes loop and timing overhead. Excludes I/O, JSON decoding, a network, "
                  "LLM inference and analyst response. Escalations latch once per scope. This is a microbenchmark.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    encoded = json.dumps(benchmark(), indent=2) + "\n"
    if args.output:
        args.output.write_text(encoded)
    else:
        print(encoded, end="")
