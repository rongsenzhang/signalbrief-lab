"""Run a read-only coverage check on the pinned Loghub OpenSSH template sample."""
import argparse
import csv
import hashlib
import io
import json
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from signalbrief.model import MIN_SCORE, router


REVISION = "dd61d0952749ee7963bde24220d1be5ede023033"
SOURCE_PATH = "OpenSSH/OpenSSH_2k.log_structured.csv"
SOURCE_URL = f"https://raw.githubusercontent.com/logpai/loghub/{REVISION}/{SOURCE_PATH}"
SOURCE_BLOB = "2ee6285ba8635e97a5f1f3148b8d126a40e2c4fd"
RELEASE = ROOT / "reference" / "corpus-check.json"


def summary(labels):
    total = sum(labels.values())
    abstained = labels["Uncertain"]
    return {
        "total": total,
        "routed": total - abstained,
        "abstained": abstained,
        "routing_coverage": round((total - abstained) / total, 4),
        "abstention_rate": round(abstained / total, 4),
        "predicted_labels": dict(sorted(labels.items())),
    }


def evaluate(source):
    header = f"blob {len(source)}\0".encode("ascii")
    if hashlib.sha1(header + source).hexdigest() != SOURCE_BLOB:
        raise ValueError("Dataset bytes differ from the pinned Git blob.")
    counts = Counter()
    templates = {}
    reader = csv.DictReader(io.StringIO(source.decode("utf-8-sig"), newline=""))
    if not {"EventId", "EventTemplate"} <= set(reader.fieldnames or ()):
        raise ValueError("Missing template fields.")
    for record in reader:
        event_id = record["EventId"]
        template = record["EventTemplate"]
        if not event_id or not template or templates.setdefault(event_id, template) != template:
            raise ValueError("Each nonempty template identifier must map to one template.")
        counts[event_id] += 1
    if not templates:
        raise ValueError("Expected a nonempty template population.")
    classifier = router()
    unique_labels = Counter()
    weighted_labels = Counter()
    for event_id, template in templates.items():
        label = classifier.predict(template)["label"]
        unique_labels[label] += 1
        weighted_labels[label] += counts[event_id]
    return {
        "schema_version": 1,
        "source": {"repository": "logpai/loghub", "revision": REVISION, "path": SOURCE_PATH,
                   "git_blob_sha1": SOURCE_BLOB, "bytes_sha256": hashlib.sha256(source).hexdigest()},
        "input_fields": ["EventId", "EventTemplate"],
        "router": {"type": "multinomial naive Bayes", "abstention_threshold": MIN_SCORE,
                   "training_fixture_sha256": hashlib.sha256((ROOT / "fixtures" / "routing_corpus.json").read_bytes()).hexdigest()},
        "unique_template_coverage": summary(unique_labels),
        "row_weighted_coverage": summary(weighted_labels),
        "most_frequent_template_row_count": max(counts.values()),
        "interpretation": "Coverage counts a non-abstaining route. The source supplies no matching service-routing or incident labels.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Read the byte-identical upstream CSV from disk instead of downloading.")
    parser.add_argument("--check", action="store_true", help="Compare the computed result with the release aggregate.")
    args = parser.parse_args()
    if args.input:
        source = args.input.read_bytes()
    else:
        with urllib.request.urlopen(SOURCE_URL, timeout=30) as response:
            source = response.read()
    result = evaluate(source)
    if args.check:
        if result != json.loads(RELEASE.read_text()):
            raise SystemExit("The computed result differs from the release aggregate.")
        print("The pinned source reproduces the release aggregate.")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
