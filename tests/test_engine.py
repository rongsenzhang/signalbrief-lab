import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_demo import case_inputs, payload
from signalbrief.engine import InvalidInput, triage
from signalbrief.model import router


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.case, self.scope, self.rows = next(case_inputs())

    def test_static_replay_matches_api_engine(self):
        actual = json.loads((ROOT / "docs/data/scenarios.json").read_text())
        self.assertEqual(payload(), actual)

    def test_evidence_is_observable_and_current(self):
        for case, scope, rows in case_inputs():
            frames = triage(scope, rows)["frames"]
            for index, frame in enumerate(frames):
                so_far = [event["id"] for event in rows[:index+1]]
                self.assertEqual(frame["event_ids"], so_far)
                self.assertTrue(set(frame["evidence_ids"]).issubset(so_far))
                self.assertEqual(frame, triage(scope, rows[:index+1])["frames"][-1])
        frames = triage(self.scope, self.rows)["frames"]
        self.assertEqual([f["priority"] for f in frames], ["Review", "Review", "High"])
        self.assertEqual(frames[-1]["evidence_ids"], ["E1012", "E1013"])

    def test_timeout_and_inclusive_boundary(self):
        rows = [dict(row) for row in self.rows]
        rows[-1]["time"] = "2026-11-16T09:18:00Z"
        self.assertEqual(triage(self.scope, rows)["frames"][-1]["priority"], "High")
        rows[-1]["time"] = "2026-11-16T09:18:01Z"
        self.assertEqual(triage(self.scope, rows)["frames"][-1]["priority"], "Review")

    def test_escalation_is_latched_for_human_review(self):
        rows = self.rows + [{"id":"E1999","time":"2026-11-16T09:59:00Z","signal":"owner_confirms"}]
        frame = triage(self.scope, rows)["frames"][-1]
        self.assertEqual(frame["priority"], "High")
        self.assertEqual(frame["evidence_ids"], ["E1012","E1013"])

    def test_conflicting_reports_cite_both_accounts_in_either_order(self):
        for first, second in (("owner_confirms", "owner_disputes"), ("owner_disputes", "owner_confirms")):
            rows = [self.rows[1], dict(self.rows[2], signal=first),
                    dict(self.rows[2], id="E1014", signal=second)]
            result = triage(self.scope, rows)["frames"][-1]
            with self.subTest(first=first):
                self.assertEqual(result["priority"], "High")
                self.assertEqual(result["rule"], "identity_conflict")
                self.assertEqual(result["evidence_ids"], ["E1012", "E1013", "E1014"])

    def test_earlier_session_confirmation_does_not_resolve_a_new_session(self):
        rows = [self.rows[1], dict(self.rows[2], signal="owner_confirms"),
                dict(self.rows[2], id="E1014", signal="session_opened"), dict(self.rows[2], id="E1015")]
        frame = triage(self.scope, rows)["frames"][-1]
        self.assertEqual(frame["rule"], "identity_high")
        self.assertEqual(frame["evidence_ids"], ["E1014", "E1015"])

    def test_cases_exercise_benign_and_inconclusive_outcomes(self):
        results = [triage(scope, rows)["frames"][-1]["priority"] for _, scope, rows in case_inputs()]
        self.assertEqual(results, ["High","High","Review","Routine","Routine","Review"])

    def test_duplicate_ids_scope_and_unknown_fields_rejected(self):
        for rows in ([self.rows[0], self.rows[0]],
                     [dict(self.rows[0], signal="backup_late")],
                     [dict(self.rows[0], user="real@example.invalid")],
                     [dict(self.rows[0], id="real@example.invalid")],
                     [dict(self.rows[0], time="2026-02-30T00:00:00Z")],
                     [self.rows[1], self.rows[0]], [], self.rows * 11):
            with self.subTest(rows=rows), self.assertRaises(InvalidInput):
                triage(self.scope, rows)

    def test_router_abstains_on_unknown(self):
        self.assertEqual(router().predict("Review requested.")["label"], "Uncertain")

    def test_corpus_splits_disjoint(self):
        data = json.loads((ROOT/"fixtures/routing_corpus.json").read_text())
        train = {r.lower() for rows in data["train"].values() for r in rows}
        held = {r.lower() for groups in data["holdout_groups"].values() for rows in groups.values() for r in rows}
        self.assertFalse(train & held)
