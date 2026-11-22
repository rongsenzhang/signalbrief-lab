import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import llm_routing as routing


class RoutingComparisonTests(unittest.TestCase):
    def test_balanced_assignment_removes_constant_letter_bias(self):
        for i in range(len(routing.LABELS)):
            self.assertEqual({order[i] for order in routing.ORDERS}, set(routing.LABELS))
        vectors = [[(4 if topic == "Telemetry" else 0) + (8 if index == 0 else 0)
                    for index, topic in enumerate(order)] for order in routing.ORDERS]
        result = routing.choose(vectors)
        self.assertEqual(result["label"], "Telemetry")
        self.assertEqual(len(set(result["per_order_labels"])), 5)
        self.assertGreater(result["mean_logits"]["Telemetry"], result["mean_logits"]["Identity"])
        with self.assertRaises(ValueError):
            routing.choose(vectors[:-1])

    def test_freeze_and_report_binding(self):
        corpus = json.loads(routing.CORPUS.read_text())
        data = routing.build(corpus, lambda prompt: [1, 2, 3, 4, 5], {"engine": "test"})
        self.assertEqual(data["measurement"]["forward_passes"], 120)
        self.assertEqual(data["summary"]["naive_bayes"]["correct"], 23)
        self.assertEqual(data["summary"]["majority"]["correct"], 6)
        self.assertEqual(len({r["group"] for r in data["rows"]}), 12)
        routing.validate(corpus, data)
        corrupt = copy.deepcopy(data)
        corrupt["rows"][0]["qwen"] = "Uncertain"
        with self.assertRaises(ValueError):
            routing.validate(corpus, corrupt)
        corpus["holdout_groups"]["Identity"]["credential-check"][0] += " edited"
        with self.assertRaises(ValueError):
            routing.holdout(corpus)

    def test_published_snapshot_recalculates_against_frozen_holdout(self):
        corpus = json.loads(routing.CORPUS.read_text())
        snap = json.loads(routing.OUTPUT.read_text())
        routing.validate(corpus, snap)
        self.assertEqual(snap["measurement"]["examples"], len(snap["rows"]))
        self.assertEqual(snap["measurement"]["forward_passes"], len(snap["rows"]) * len(routing.ORDERS))

    def test_abstention_counts_as_a_miss_on_a_labelled_example(self):
        rows = [{"expected": "Telemetry", "guess": "Uncertain"}, {"expected": "Identity", "guess": "Identity"}]
        summary = routing.metrics(rows, "guess")
        self.assertEqual((summary["correct"], summary["abstained"], summary["accuracy"]), (1, 1, .5))
        self.assertEqual(summary["confusion"]["Telemetry"]["Uncertain"], 1)
        self.assertEqual(summary["per_class_f1"]["Telemetry"], 0)


if __name__ == "__main__":
    unittest.main()
