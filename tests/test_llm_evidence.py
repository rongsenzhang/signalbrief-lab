import copy
import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
module = importlib.util.spec_from_file_location("llm_evidence", ROOT / "scripts/llm_evidence.py")
llm = importlib.util.module_from_spec(module)
module.loader.exec_module(llm)


class EvidenceProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = llm.read_json(llm.PROTOCOL)
        cls.data = llm.read_json(llm.DATA)
        cls.digest = hashlib.sha256(llm.DATA.read_bytes()).hexdigest()

    def test_unmapped_choice_and_instructions_cannot_produce_a_citation(self):
        events = [{"id": "obs-1"}]
        for answer in ("Z", "A. Ignore all other records", "A or B", "a", ""):
            self.assertIsNone(llm.parse(answer, events, self.protocol))
        self.assertEqual(llm.parse("A.", events, self.protocol), "obs-1")
        self.assertEqual(llm.parse("X", events, self.protocol), "abstain")

    def test_disagreement_and_abstention(self):
        self.assertEqual(llm.decide(["x", "y"]), (None, "ordering changed the choice"))
        self.assertEqual(llm.decide(["x", "abstain"]), (None, "model abstained"))
        self.assertEqual(llm.decide(["x", None]), (None, "invalid response"))

    def test_fixture_and_source_binding(self):
        # Always returning A simulates positional bias only; this is not model inference.
        snapshot = llm.make_snapshot(self.data, self.protocol, lambda _: "A", {"engine": "unit test"}, self.digest)
        result = llm.validate(self.data, self.protocol, snapshot, self.digest)
        self.assertGreater(result["multi_event_frames"], 0)
        self.assertEqual(result["multi_event_selected"], 0)
        self.assertEqual(result["unstable_order"], result["multi_event_frames"])
        sample = self.data["scenarios"][0]["id"]
        altered = copy.deepcopy(snapshot)
        altered["scenarios"][sample][0]["extract"] = "An unobserved event."
        with self.assertRaises(ValueError):
            llm.validate(self.data, self.protocol, altered, self.digest)
        with self.assertRaises(ValueError):
            llm.validate(self.data, self.protocol, snapshot, "stale")

    def test_later_event_is_inaccessible(self):
        sample = copy.deepcopy(self.data["scenarios"][0])
        sample["frames"][0]["event_ids"] = [sample["events"][-1]["id"]]
        with self.assertRaises(ValueError):
            llm.observed(sample, 0)

    def test_baseline_uses_same_multi_event_denominator(self):
        snapshot = llm.make_snapshot(self.data, self.protocol, lambda _: "X", {}, self.digest)
        result = llm.validate(self.data, self.protocol, snapshot, self.digest)
        frames = [f for s in self.data["scenarios"] for f in s["frames"] if len(f["event_ids"]) > 1]
        self.assertEqual(result["most_recent_matches"], sum(f["event_ids"][-1] in f["evidence_ids"] for f in frames))
        self.assertEqual(result["model_abstained"], result["frames"])
        self.assertEqual(result["multi_event_matches"], 0)


if __name__ == "__main__":
    unittest.main()
