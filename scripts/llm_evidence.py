"""Run a frozen instruction model on observed synthetic events, or verify a saved run."""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/data/scenarios.json"
PROTOCOL = ROOT / "docs/model/protocol.json"
SNAPSHOT = ROOT / "docs/data/language-model.json"
METHOD = "Two deterministic letter choices in opposite candidate orders"


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def observed(scenario, index):
    events = scenario["events"][:index + 1]
    ids = [event["id"] for event in events]
    if len(ids) != len(set(ids)) or scenario["frames"][index]["event_ids"] != ids:
        raise ValueError("Replay frame does not match its event prefix")
    return events


def prompt(protocol, reason, ordered):
    labels = protocol["labels"]
    if not 1 <= len(ordered) <= len(labels):
        raise ValueError("Candidate count is outside the protocol")
    lines = ["{}: {} — {}".format(label, event["source"], event["text"])
             for label, event in zip(labels, ordered)]
    body = "\n".join(["Current finding: " + reason, "Observations:", *lines,
                      "X: Insufficient evidence.", protocol["question"]])
    return [{"role": "system", "content": protocol["system"]},
            {"role": "user", "content": body}]


def parse(response, ordered, protocol):
    match = re.fullmatch(r"([A-Z])\.?", " ".join(response.split()))
    if not match:
        return None
    choice = match.group(1)
    if choice == protocol["abstain"]:
        return "abstain"
    labels = protocol["labels"][:len(ordered)]
    return ordered[labels.index(choice)]["id"] if choice in labels else None


def decide(choices):
    if None in choices:
        return None, "invalid response"
    if "abstain" in choices:
        return None, "model abstained"
    if choices[0] != choices[1]:
        return None, "ordering changed the choice"
    return choices[0], "consistent choice"


def make_snapshot(data, protocol, infer, runtime, digest):
    snapshot = {
        "schema_version": 1, "status": "ready", "model_id": protocol["model_id"],
        "revision": protocol["revision"], "method": METHOD, "runtime": runtime,
        "protocol_version": protocol["protocol_version"], "input_sha256": digest,
        "scenarios": {}
    }
    for scenario in data["scenarios"]:
        records = []
        for index, frame in enumerate(scenario["frames"]):
            events = observed(scenario, index)
            ordered_views = [events, list(reversed(events))]
            # A single candidate has no order effect; reuse the identical model call.
            first = infer(prompt(protocol, frame["reason"], events))
            other = first if len(events) == 1 else infer(prompt(protocol, frame["reason"], ordered_views[1]))
            raw = [first, other]
            choices = [parse(response, view, protocol) for response, view in zip(raw, ordered_views)]
            selected, outcome = decide(choices)
            extract = next((e["text"] for e in events if e["id"] == selected), None)
            records.append({"event_ids": frame["event_ids"], "selected_id": selected,
                            "extract": extract, "outcome": outcome, "responses": raw})
        snapshot["scenarios"][scenario["id"]] = records
    return snapshot


def validate(data, protocol, snapshot, digest):
    if (snapshot.get("schema_version"), snapshot.get("status"), snapshot.get("input_sha256"),
        snapshot.get("model_id"), snapshot.get("revision"), snapshot.get("protocol_version")) != (
            1, "ready", digest, protocol["model_id"], protocol["revision"], protocol["protocol_version"]):
        raise ValueError("Snapshot provenance or input fingerprint does not match")
    if set(snapshot["scenarios"]) != {scenario["id"] for scenario in data["scenarios"]}:
        raise ValueError("Scenario set does not match")
    counts = Counter(frames=0, selected=0, among_rule_citations=0, multi_event_frames=0,
                     multi_event_selected=0, multi_event_matches=0, most_recent_matches=0,
                     model_abstained=0, invalid_response=0, unstable_order=0)
    for scenario in data["scenarios"]:
        records = snapshot["scenarios"][scenario["id"]]
        if len(records) != len(scenario["frames"]) or len(records) != len(scenario["events"]):
            raise ValueError("Frame count does not match")
        for index, record in enumerate(records):
            events = observed(scenario, index)
            if record["event_ids"] != [e["id"] for e in events]:
                raise ValueError("Observation IDs do not match")
            raw = record["responses"]
            if not isinstance(raw, list) or len(raw) != 2 or any(not isinstance(x, str) for x in raw):
                raise ValueError("Missing model responses")
            choices = [parse(raw[0], events, protocol), parse(raw[1], list(reversed(events)), protocol)]
            selected, outcome = decide(choices)
            extract = next((e["text"] for e in events if e["id"] == selected), None)
            if (record["selected_id"], record["outcome"], record["extract"]) != (selected, outcome, extract):
                raise ValueError("Selected evidence is inconsistent with original observation or model outputs")
            counts["frames"] += 1
            citations = scenario["frames"][index]["evidence_ids"]
            if selected:
                counts["selected"] += 1
                counts["among_rule_citations"] += selected in citations
            else:
                key = {"model abstained": "model_abstained", "invalid response": "invalid_response",
                       "ordering changed the choice": "unstable_order"}[outcome]
                counts[key] += 1
            if len(events) > 1:
                counts["multi_event_frames"] += 1
                counts["multi_event_selected"] += selected is not None
                counts["multi_event_matches"] += selected in citations
                counts["most_recent_matches"] += events[-1]["id"] in citations
    return dict(counts)


def load_model(protocol):
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(0)
    torch.set_num_threads(min(torch.get_num_threads(), 4))
    options = {"revision": protocol["revision"], "trust_remote_code": False}
    tokenizer = AutoTokenizer.from_pretrained(protocol["model_id"], **options)
    model = AutoModelForCausalLM.from_pretrained(
        protocol["model_id"], torch_dtype=torch.float32, use_safetensors=True, **options
    ).eval()
    tokenizer.pad_token_id = tokenizer.eos_token_id

    @torch.inference_mode()
    def infer(messages):
        ids = tokenizer.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt")
        completed = model.generate(ids, attention_mask=torch.ones_like(ids),
                                   do_sample=False, max_new_tokens=4, pad_token_id=tokenizer.pad_token_id)
        return tokenizer.decode(completed[0, ids.shape[-1]:], skip_special_tokens=True).strip()

    runtime = {"engine": "PyTorch CPU", "torch": str(torch.__version__),
               "transformers": transformers.__version__, "precision": "float32", "sampling": "greedy"}
    return infer, runtime


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate", action="store_true", help="check an existing ready snapshot without model dependencies")
    parser.add_argument("--output", type=Path, default=SNAPSHOT)
    args = parser.parse_args()
    data, protocol = read_json(DATA), read_json(PROTOCOL)
    digest = hashlib.sha256(DATA.read_bytes()).hexdigest()
    if args.validate:
        snapshot = read_json(args.output)
    else:
        infer, runtime = load_model(protocol)
        snapshot = make_snapshot(data, protocol, infer, runtime, digest)
    measures = validate(data, protocol, snapshot, digest)
    print(json.dumps(measures, sort_keys=True))
    if not args.validate:
        snapshot["evaluation"] = measures
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(".tmp")
        temporary.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temporary.replace(args.output)


if __name__ == "__main__":
    main()
