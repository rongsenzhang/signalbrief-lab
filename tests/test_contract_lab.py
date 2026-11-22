"""Integration examples stay in sync with the authenticated API and its policy boundary."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from contract_examples import examples


class ContractLabTests(unittest.TestCase):
    def test_examples_match_current_api(self):
        published = json.loads((ROOT / "docs/data/contract-examples.json").read_text())
        self.assertEqual(examples(), published)
        self.assertEqual(len(published), 10)

    def test_change_report_and_window(self):
        pairs = examples()
        for signal, inside in (("owner_disputes", "High"), ("owner_confirms", "Routine")):
            for minutes in (1, 5, 15, 16, 30):
                with self.subTest(signal=signal, minutes=minutes):
                    frame = pairs[f"{signal}-{minutes}"]["response"]["frames"][-1]
                    self.assertEqual(frame["priority"], inside if minutes <= 15 else "Review")
                    self.assertEqual(frame["evidence_ids"], ["E5001", "E5002"] if minutes <= 15 else ["E5002"])
