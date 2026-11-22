import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import handover_drafts as draft


class HandoverDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = draft.read(draft.INPUT)
        cls.packets = draft.source_packets(cls.data)

    def test_uses_only_final_cited_observations(self):
        packet = self.packets["SB-101"]
        self.assertEqual([record["id"] for record in packet["sources"]], ["E1012", "E1013"])
        prompt = draft.messages(packet, "manager")[1]["content"]
        self.assertIn(packet["known_limit"], prompt)
        for event in packet["sources"]:
            self.assertIn(event["text"], prompt)
        self.assertNotIn("E1011", prompt)
        self.assertNotIn("Verify the report", prompt)
        self.assertNotEqual(draft.messages(packet, "analyst"), draft.messages(packet, "manager"))

    def test_refuses_modified_source(self):
        data = copy.deepcopy(self.data)
        data["scenarios"][0]["events"][1]["text"] = "Unreviewed additional observation."
        with self.assertRaises(ValueError):
            draft.source_packets(data)

    def test_overstatement_and_foreign_reference_are_flagged(self):
        text = "The attacker compromised the session and the owner disputed it. Reset the password. See E9999."
        status, flags = draft.screen(text, self.packets["SB-101"])
        self.assertEqual(status, "flagged")
        self.assertTrue(any("cause" in flag for flag in flags))
        self.assertTrue(any("intervention" in flag for flag in flags))
        self.assertTrue(any("event outside" in flag for flag in flags))

    def test_contradictions_and_omissions_never_clear_a_draft(self):
        samples = [
            ("SB-103", "The delayed backup was verified."),
            ("SB-104", "The owner did not recognise the sign-in session."),
            ("SB-106", "The feed resumed and the gap was filled."),
        ]
        for case_id, text in samples:
            with self.subTest(case_id=case_id):
                self.assertIn("Possible reversal of the recorded finding", draft.screen(text, self.packets[case_id])[1])
        status, flags = draft.screen("The feed has resumed.", self.packets["SB-106"])
        self.assertEqual(status, "flagged")
        self.assertTrue(any("missing interval" in flag for flag in flags))
        self.assertEqual(draft.screen("The feed resumed after a gap.", self.packets["SB-106"]), ("requires review", []))
        self.assertEqual(draft.screen("ABSTAIN", self.packets["SB-106"]), ("abstained", []))

    def test_metadata_and_flags_cannot_be_silently_changed(self):
        artifact = draft.snapshot(self.data, lambda prompt: "ABSTAIN", {"engine": "unit test"})
        draft.validate(self.data, artifact)
        altered = copy.deepcopy(artifact)
        altered["cases"]["SB-101"]["drafts"]["analyst"]["status"] = "approved"
        with self.assertRaises(ValueError):
            draft.validate(self.data, altered)
        altered = copy.deepcopy(artifact)
        altered["cases"]["SB-101"]["sources"] = []
        with self.assertRaises(ValueError):
            draft.validate(self.data, altered)

    def test_recorded_editorial_review_matches_the_actual_drafts(self):
        review = draft.read(ROOT / "docs/data/handover-review.json")
        artifact = draft.read(draft.OUTPUT)
        self.assertEqual(review["snapshot_sha256"], hashlib.sha256(draft.OUTPUT.read_bytes()).hexdigest())
        self.assertEqual(review["workflow_run"], artifact["runtime"]["workflow_run"])
        self.assertEqual(set(review["cases"]), set(artifact["cases"]))
        for case_id, case in artifact["cases"].items():
            assessments = review["cases"][case_id]
            self.assertEqual(set(assessments), set(case["drafts"]))
            for role, item in case["drafts"].items():
                audit = assessments[role]
                self.assertEqual(audit["draft_sha256"], hashlib.sha256(item["text"].encode()).hexdigest())
                self.assertEqual(audit["evidence_ids"], [source["id"] for source in case["sources"]])
                self.assertIn(audit["verdict"], {"supported", "supported with omission", "contains unsupported claims"})
                self.assertTrue(audit["note"].strip())

    def test_published_snapshot_when_ready(self):
        artifact = draft.read(draft.OUTPUT)
        if artifact["status"] == "pending":
            self.assertEqual(artifact["cases"], {})
        else:
            draft.validate(self.data, artifact)


if __name__ == "__main__":
    unittest.main()
