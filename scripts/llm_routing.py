"""Compare frozen Qwen topic routing against the published synthetic hold-out and baselines."""
import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from signalbrief.model import Router

CORPUS = ROOT / "fixtures/routing_corpus.json"
OUTPUT = ROOT / "docs/data/llm-routing.json"
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
LABELS = ["Identity", "Endpoint", "Service continuity", "Telemetry", "Uncertain"]
DESCRIPTIONS = {
    "Identity": "Accounts, authentication and ownership of access.",
    "Endpoint": "The behaviour of applications or controls on a device.",
    "Service continuity": "The ability to back up and recover a service.",
    "Telemetry": "The collection and availability of monitoring observations.",
    "Uncertain": "The message provides too little evidence to select any topic.",
}
LETTERS = "ABCDE"
SYSTEM = "Route a short service-desk observation to its main topic. Return exactly one letter."
ORDERS = [LABELS[start:] + LABELS[:start] for start in range(len(LABELS))]
PROTOCOL = "qwen-next-letter-balanced/1"
FROZEN_CORPUS = "5407d9391a4036723d007fd857f3d30fe3f1d3b1b174f3f9ffb8ed9948710c3e"


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def messages(observation, order):
    options = "\n".join(f"{letter}. {label} — {DESCRIPTIONS[label]}" for letter, label in zip(LETTERS, order))
    return [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{options}\n\nObservation: {observation}\nAnswer with one letter."}]


def holdout(corpus):
    if fingerprint(corpus) != FROZEN_CORPUS:
        raise ValueError("The corpus differs from the preregistered release")
    return [{"expected": label, "group": group, "text": text}
            for label, groups in corpus["holdout_groups"].items()
            for group, texts in groups.items() for text in texts]


def choose(vectors):
    if len(vectors) != len(ORDERS):
        raise ValueError("One score vector per label rotation is required")
    scores = {label: [] for label in LABELS}
    top = []
    for order, logits in zip(ORDERS, vectors):
        if (len(logits) != len(LABELS) or any(not isinstance(v, (float, int)) or not math.isfinite(v) for v in logits)):
            raise ValueError("Each rotation requires five finite next-token logits")
        top.append(order[max(range(len(order)), key=logits.__getitem__)])
        for label, logit in zip(order, logits):
            scores[label].append(logit)
    means = {label: round(statistics.mean(values), 6) for label, values in scores.items()}
    return {"label": max(means, key=means.get), "mean_logits": means, "per_order_labels": top}


def metrics(rows, field):
    matrix = {label: {guess: 0 for guess in LABELS} for label in LABELS[:-1]}
    for row in rows:
        matrix[row["expected"]][row[field]] += 1
    correct = sum(matrix[label][label] for label in LABELS[:-1])
    f1 = {}
    for label in LABELS[:-1]:
        n = sum(matrix[label].values()) + sum(r[label] for r in matrix.values())
        f1[label] = round(2 * matrix[label][label] / n, 6) if n else 0.0
    missed = sum(row["Uncertain"] for row in matrix.values())
    return {"total": len(rows), "correct": correct, "abstained": missed,
            "accuracy": round(correct / len(rows), 6), "per_class_f1": f1,
            "macro_f1": round(statistics.mean(f1.values()), 6), "confusion": matrix}


def evaluate(rows):
    return {
        **{key: metrics(rows, key) for key in ["qwen", "naive_bayes", "majority"]},
        "all_five_orders_agree": sum(len(set(row["per_order_labels"])) == 1 for row in rows),
        "individual_order_correct_out_of_24": [sum(r["per_order_labels"][i] == r["expected"] for r in rows)
                                                  for i in range(len(ORDERS))],
    }


def baseline(corpus):
    # Use exactly the same model and training examples as the workbench. Training
    # is balanced; deterministic first-class tie breaking makes comparison explicit.
    train = corpus["train"]
    return Router(train), max(LABELS[:-1], key=lambda label: len(train[label]))


def build(corpus, score, runtime):
    examples = holdout(corpus)
    bayes, majority = baseline(corpus)
    started = time.perf_counter()
    rows = []
    for example in examples:
        text = example["text"]
        vectors = [[round(float(v), 6) for v in score(messages(text, order))] for order in ORDERS]
        result = choose(vectors)
        rows.append({**example, "qwen": result["label"], "mean_logits": result["mean_logits"],
                     "per_order_labels": result["per_order_labels"], "raw_next_token_logits": vectors,
                     "naive_bayes": bayes.predict(text)["label"], "majority": majority})
    elapsed = time.perf_counter() - started
    return {"schema_version": 1, "status": "ready", "model_id": MODEL, "revision": REVISION,
            "protocol": PROTOCOL, "corpus_sha256": FROZEN_CORPUS,
            "prompt_sha256": fingerprint([messages("{observation}", order) for order in ORDERS]),
            "letters": LETTERS, "candidate_orders": ORDERS, "runtime": runtime,
            "measurement": {"elapsed_seconds": round(elapsed, 3), "examples": len(rows),
                            "forward_passes": len(rows) * len(ORDERS),
                            "scope": "CPU scoring, tokenization, aggregation and baseline prediction. Model loading excluded."},
            "summary": evaluate(rows), "rows": rows}


def validate(corpus, snap):
    examples = holdout(corpus)
    expected = {"schema_version": 1, "status": "ready", "model_id": MODEL, "revision": REVISION,
                "protocol": PROTOCOL, "corpus_sha256": FROZEN_CORPUS, "letters": LETTERS,
                "candidate_orders": ORDERS, "prompt_sha256": fingerprint([messages("{observation}", order) for order in ORDERS])}
    if any(snap.get(k) != v for k, v in expected.items()) or len(snap["rows"]) != len(examples):
        raise ValueError("Snapshot does not match frozen protocol")
    bayes, majority = baseline(corpus)
    for example, row in zip(examples, snap["rows"]):
        result = choose(row["raw_next_token_logits"])
        valid = {**example, "qwen": result["label"], "mean_logits": result["mean_logits"],
                 "per_order_labels": result["per_order_labels"], "naive_bayes": bayes.predict(example["text"])["label"],
                 "majority": majority}
        if any(row.get(k) != v for k, v in valid.items()):
            raise ValueError("Row scores, labels or baseline predictions do not match")
    if evaluate(snap["rows"]) != snap["summary"]:
        raise ValueError("Result summaries do not match scored rows")


def load():
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.set_num_threads(min(4, torch.get_num_threads()))
    options = {"revision": REVISION, "trust_remote_code": False}
    tok = AutoTokenizer.from_pretrained(MODEL, **options)
    network = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32, use_safetensors=True, **options).eval()
    ids = [tok.encode(letter, add_special_tokens=False) for letter in LETTERS]
    if any(len(tokens) != 1 for tokens in ids) or len({tokens[0] for tokens in ids}) != len(LETTERS):
        raise ValueError("Answer letters do not map to five distinct tokens")
    indexes = [tokens[0] for tokens in ids]

    @torch.inference_mode()
    def score(prompt):
        tokens = tok.apply_chat_template(prompt, tokenize=True, add_generation_prompt=True, return_tensors="pt")
        return network(input_ids=tokens, use_cache=False).logits[0, -1, indexes].tolist()

    return score, {"engine": "PyTorch CPU", "dtype": "float32", "torch": str(torch.__version__),
                   "transformers": transformers.__version__, "threads": torch.get_num_threads(),
                   "candidate_token_ids": indexes, "workflow_run": os.environ.get("GITHUB_RUN_ID"),
                   "source_commit": os.environ.get("GITHUB_SHA")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    corpus = json.loads(CORPUS.read_text())
    if args.validate:
        snap = json.loads(args.output.read_text())
        validate(corpus, snap)
    else:
        holdout(corpus)
        score, runtime = load()
        snap = build(corpus, score, runtime)
        validate(corpus, snap)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.output.with_suffix(".tmp")
        tmp.write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n")
        tmp.replace(args.output)
    print(json.dumps(snap["summary"], indent=2))


if __name__ == "__main__":
    main()
