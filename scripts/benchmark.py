"""Measure topic routing and complete case replays. Write timings only on explicit request."""
import argparse
import json
import platform
import random
import time
from collections import Counter
from itertools import cycle
from math import ceil
from pathlib import Path

from build_demo import ROOT, case_inputs
from signalbrief.engine import triage
from signalbrief.model import FIXTURES, MIN_SCORE, router


def evaluate():
    corpus = json.loads((FIXTURES / "routing_corpus.json").read_text())
    topic_rows = []
    model = router()
    for expected, groups in corpus["holdout_groups"].items():
        for name, examples in groups.items():
            for text in examples:
                topic_rows.append(dict(text=text, group=name, expected=expected, **model.predict(text)))
    labels = list(corpus["train"])
    confusion = {label: dict(Counter(row["label"] for row in topic_rows if row["expected"] == label))
                 for label in labels}
    f1 = []
    for label in labels:
        tp = confusion[label].get(label, 0)
        actual = sum(confusion[label].values())
        predicted = sum(row.get(label, 0) for row in confusion.values())
        f1.append(2 * tp / (actual + predicted))
    probes = lambda rows: [dict(row, **model.predict(row["text"])) for row in rows]
    return {
        "model": "multinomial naive Bayes with add-one smoothing",
        "score_meaning":"Highest closed-set topic posterior from this model. Uncalibrated. It does not estimate incident probability.",
        "abstention_threshold":MIN_SCORE,
        "train_counts":{label:len(rows) for label, rows in corpus["train"].items()},
        "test_counts":{label:sum(row.values()) for label,row in confusion.items()},
        "test_groups":sum(len(groups) for groups in corpus["holdout_groups"].values()),
        "test_size": len(topic_rows), "confusion":confusion,
        "accuracy":round(sum(r["expected"] == r["label"] for r in topic_rows)/len(topic_rows),4),
        "macro_f1":round(sum(f1)/len(f1),4),
        "majority_class_accuracy":round(max(sum(row.values()) for row in confusion.values())/len(topic_rows),4),
        "rows":topic_rows,
        "low_information_probes":probes(corpus["challenge"]),
        "mixed_topic_probes":probes(corpus["mixed_topic_probes"]),
        "limits":"Manually authored synthetic wording groups in English. Training never consumes held-out phrases. Small test, shared domain vocabulary and mixed-topic failures limit generalisation. Diagnostic probes are separate from the test."
    }


def throughput(wanted):
    samples = [(scope, rows) for _, scope, rows in case_inputs()]
    router()  # Exclude one-off corpus loading.
    count = cases = 0
    # Reservoir sampling keeps latency storage fixed even for a long replay stream.
    sample_limit = 4096
    sample_ms = []
    shuffle = random.Random(2026)
    start = time.perf_counter()
    for scope, rows in cycle(samples):
        rows = rows[:wanted-count]
        t = time.perf_counter()
        triage(scope, rows)
        elapsed_ms = (time.perf_counter() - t) * 1000
        count += len(rows)
        cases += 1
        if len(sample_ms) < sample_limit:
            sample_ms.append(elapsed_ms)
        else:
            position = shuffle.randrange(cases)
            if position < sample_limit:
                sample_ms[position] = elapsed_ms
        if count == wanted:
            break
    elapsed = time.perf_counter() - start
    sample_ms.sort()
    return {
        "events":count, "cases":cases, "scenario_families":len(samples),
        "seconds":round(elapsed,3), "events_per_second":round(count/elapsed),
        "sampled_cases_for_latency":len(sample_ms),
        "per_case_p50_ms":round(sample_ms[ceil(len(sample_ms)*0.5)-1],4),
        "per_case_p95_ms":round(sample_ms[ceil(len(sample_ms)*0.95)-1],4),
        "machine":platform.machine(), "system":platform.system(), "python":platform.python_version(),
        "limits":"Single process, one caller, warm model. Repeats six short synthetic patterns (last may be truncated), including input validation, NLP, rules and brief creation. Latency percentiles use a uniform case reservoir (maximum 4,096). Excludes HTTP, UI, LLM and I/O. Throughput is a host-specific engineering measurement."
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events",type=int,default=100000)
    parser.add_argument("--output",type=Path)
    opts = parser.parse_args()
    if opts.events < 1:
        parser.error("--events must be positive")
    results = {"version":"1.0.0", "routing":evaluate(), "benchmark":throughput(opts.events)}
    encoded = json.dumps(results, indent=2) + "\n"
    if opts.output:
        opts.output.write_text(encoded)
    else:
        print(encoded, end="")
