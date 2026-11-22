import io
import json
import os
import random
import subprocess
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from build_stream_trace import build
from signalbrief.engine import SCOPES, triage
from signalbrief.stream import EventStream, stream_results


def packet(code, number, minute=0, second=0, scope="ACCESS-A"):
    return {"scope": scope, "id": f"E{number:04}", "time": f"2026-11-16T09:{minute:02}:{second:02}Z", "signal": code}


class StreamTests(unittest.TestCase):
    def test_published_trace_and_fixture_contracts_reproduce(self):
        trace = build()
        self.assertEqual(trace, json.loads((ROOT / "docs/data/stream-trace.json").read_text()))
        self.assertEqual(len(trace["contract_checks"]), 10)

    def test_corroboration_and_inclusive_time_boundary(self):
        for seconds, expected in ((0, "High"), (1, "Review")):
            stream = EventStream()
            first = stream.ingest(packet("session_opened", 1))
            self.assertEqual(first["transition"], {"from": None, "to": "Review"})
            self.assertFalse(first["alert"])
            current = stream.ingest(packet("owner_disputes", 2, 15, seconds))
            self.assertEqual(current["priority"], expected)
            self.assertEqual(current["alert"], seconds == 0)
            self.assertEqual(current["evidence_ids"], ["E0001", "E0002"] if seconds == 0 else ["E0002"])

    def test_interleaving_duplicate_conflict_and_late_are_isolated(self):
        stream = EventStream()
        session = packet("session_opened", 1)
        dispute = packet("owner_disputes", 2, 5)
        stream.ingest(session)
        device = stream.ingest(packet("endpoint_block", 1, 8, scope="DEVICE-A"))
        self.assertEqual(device["previous_priority"], None)
        self.assertTrue(stream.ingest(dispute)["alert"])
        self.assertEqual(stream.ingest(session)["status"], "duplicate")
        self.assertEqual(stream.ingest(dispute)["status"], "duplicate")
        self.assertEqual(stream.ingest(dict(dispute, signal="owner_confirms"))["code"], "conflict")
        late = packet("owner_confirms", 3, 3)
        self.assertEqual(stream.ingest(late)["code"], "late")
        current = stream.ingest(packet("owner_confirms", 3, 6))
        self.assertFalse(current["alert"])
        self.assertIsNone(current["transition"])
        self.assertEqual(current["evidence_ids"], ["E0001", "E0002", "E0003"])
        self.assertTrue(stream.ingest(packet("process_observed", 2, 9, scope="DEVICE-A"))["alert"])

    def test_schema_rejection_and_line_recovery(self):
        row = json.dumps(packet("session_opened", 1)).encode()
        lines = io.BytesIO(b'{"scope":1,"scope":2}\n' + b"x" * 5000 + b"\n" + b'{"customer":"private"}\n' + row + b"\n" + row)
        responses = list(stream_results(lines))
        self.assertEqual([r.get("code", r["status"]) for r in responses],
                         ["invalid_json", "line_too_long", "schema", "accepted", "duplicate"])
        self.assertNotIn("private", json.dumps(responses))

    def test_compact_stream_and_batch_findings_agree_on_repeated_signals(self):
        rng = random.Random(10407)
        for scope, codes in SCOPES.items():
            for trial in range(16):
                data = []
                instant = datetime(2026, 11, 16, 9)
                stream = EventStream()
                for idx in range(32):
                    instant += timedelta(seconds=rng.choice([0, 10, 90, 901]))
                    record = {"id": f"E{idx:04}", "time": instant.isoformat() + "Z",
                              "signal": rng.choice(sorted(codes))}
                    data.append(record)
                    out = stream.ingest(dict(record, scope=scope))
                    frame = triage(scope, data)["frames"][-1]
                    with self.subTest(scope=scope, trial=trial, step=idx):
                        for field in ("priority", "rule", "reason", "evidence_ids"):
                            self.assertEqual(out[field], frame[field])

    def test_demo_and_stdin_run_the_same_pipeline(self):
        command = [sys.executable, "-m", "signalbrief.stream"]
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        demo = subprocess.check_output(command + ["--demo"], env=env)
        sample = (ROOT / "fixtures/stream-demo.ndjson").read_bytes()
        stdin = subprocess.check_output(command, input=sample, env=env)
        self.assertEqual(demo, stdin)
        rows = [json.loads(line) for line in demo.splitlines()]
        self.assertEqual([r["event_id"] for r in rows if r.get("alert")], ["E7002"])
        self.assertEqual(sum(r["status"] == "accepted" for r in rows), 5)
        self.assertEqual([r["code"] for r in rows if r["status"] == "rejected"], ["late", "conflict"])
