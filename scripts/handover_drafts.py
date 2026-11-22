"""Generate and verify two role-specific LLM handovers using the public synthetic cases."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "docs/data/scenarios.json"
OUTPUT = ROOT / "docs/data/handover-drafts.json"
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
PROTOCOL = "observed-handover/1"
ROLES = {
    "manager": "You are writing for a service owner. Use everyday language. Explain what happened and what is still uncertain.",
    "analyst": "You are writing for the analyst taking the next shift. Describe the two observations precisely and preserve the limits of the evidence.",
}

# These rule-specific semantic probes highlight common omissions and overclaims.
# They do not establish entailment. All output still requires human verification.
PROBES = {
    "identity_high": [
        ("the new session", r"session|sign[ -]?in|log[ -]?in|logg?ed"),
        ("the owner's dispute", r"(?:not|n.t|never|un|did not).{0,22}(?:recogn|acknowledg|authoriz|authoris|familiar)|disput|unfamiliar|denied"),
    ],
    "endpoint_high": [
        ("the protection block", r"block|stopp|prevent"),
        ("the separate observation of a running process", r"running|still active|continued|remained active"),
    ],
    "backup_pending": [
        ("the missed window", r"late|delay|missed|overdue|behind"),
        ("the outstanding check", r"pending|waiting|await|no result|still.{0,18}(?:check|verify)|not.{0,20}(?:verified|known|confirmed)|unknown|unverified|uncertain|no.{0,20}verification"),
    ],
    "identity_recognised": [
        ("owner recognition", r"recogn[iy][sz]|owner.{0,20}confirm|confirm.{0,20}own|acknowledg"),
        ("the relevant session", r"session|sign[ -]?in|log[ -]?in|logg?ed"),
    ],
    "backup_verified": [
        ("the delayed backup", r"late|delay|missed|overdue|behind"),
        ("the tested recovery copy", r"usab|restor|recover"),
    ],
    "feed_return": [
        ("the missing interval", r"gap|missing|blank|interruption"),
        ("the feed resuming", r"resum|back|restart|return|again"),
    ],
}
OVERCLAIMS = [
    ("Compromise or cause needs a source", r"\b(?:compromised|hacked|attack(?:er)?|malware|breach|root cause|unauthori[sz]ed)\b"),
    ("Check any assertion about loss, safety or business impact", r"\b(?:data (?:was |were )?(?:lost|stolen)|no data loss|safe|secure|no impact|no risk|all systems|fully recover(?:ed|able))\b"),
    ("A new intervention or instruction was introduced", r"\b(?:reset|delete|investigat\w*|you should|must|need to|recommend|disable|quarantine|disconnect|immediately|patch)\b"),
]
CONTRADICTIONS = {
    "identity_high": r"owner (?:has |had )?(?:confirmed|recognised|recognized|approved) (?:the |this )?(?:sign|session|access)|owner.{0,15}successfully (?:signed|logged) in",
    "endpoint_high": r"(?:process|application).{0,18}(?:no longer running|removed|terminated)|inventory.{0,18}confirmed.{0,14}block",
    "backup_pending": r"successfully restor|(?:restore|backup) (?:was |is |has been )?(?:successful|verified|usable|complete)|(?:backup|data) (?:was |is )?lost",
    "identity_recognised": r"(?:not|n.t|never|un).{0,10}recogni[sz]|unfamiliar|disputed",
    "backup_verified": r"no usable copy|failed (?:to )?restor|copy (?:is |was )?unusable|(?:unable|cannot|could not) (?:to )?recover",
    "feed_return": r"all.{0,16}(?:events|records|data).{0,20}(?:recovered|available)|gap (?:was |is )?(?:filled|resolved)|feed.{0,12}(?:still|remains) (?:down|offline)",
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_packets(data):
    """Only accept prepared event text from the synthetic signal catalogue."""
    catalogue = read(ROOT / "fixtures/signals.json")
    cases = {case["id"]: case for case in read(ROOT / "fixtures/cases.json")}
    packets = {}
    for case in data["scenarios"]:
        case_id, events = case["id"], case["events"]
        if case_id in packets or case_id not in cases:
            raise ValueError("Unexpected or repeated case")
        if [event["signal"] for event in events] != cases[case_id]["signals"]:
            raise ValueError("Observations differ from the approved synthetic scenario")
        for event in events:
            if [event["source"], event["text"]] != catalogue[event["signal"]]:
                raise ValueError("Event text is outside the approved synthetic catalogue")
        frame = case["frames"][-1]
        ids = [event["id"] for event in events]
        if (frame["event_ids"] != ids or len(set(ids)) != len(ids)
                or frame["rule"] not in PROBES or not frame["evidence_ids"]
                or not set(frame["evidence_ids"]) <= set(ids)):
            raise ValueError("Invalid final-frame provenance")
        sources = [{k: event[k] for k in ("id", "source", "text")} for event in events
                   if event["id"] in frame["evidence_ids"]]
        packets[case_id] = {"sources": sources, "known_limit": frame["unknown"], "rule": frame["rule"]}
    if set(packets) != set(cases):
        raise ValueError("Incomplete scenario set")
    return packets


def messages(packet, role):
    evidence = "\n".join(f'{row["id"]} | {row["source"]}: {row["text"]}' for row in packet["sources"])
    system = ("Write one short handover of at most two sentences. Use only the supplied observations "
              "and evidence limit. Do not add causes, impact, advice or conclusions. Write the handover "
              "only, with no heading. If there is too little evidence, respond ABSTAIN.")
    return [{"role": "system", "content": system},
            {"role": "user", "content": f'{ROLES[role]}\nObservations:\n{evidence}\nEvidence limit: {packet["known_limit"]}'}]


def screen(text, packet):
    if text.strip().upper().rstrip(".") == "ABSTAIN":
        return "abstained", []
    flags = [message for message, pattern in OVERCLAIMS if re.search(pattern, text, re.I)]
    rule = packet["rule"]
    if re.search(CONTRADICTIONS[rule], text, re.I):
        flags.append("Possible reversal of the recorded finding")
    for fact, pattern in PROBES[rule]:
        if not re.search(pattern, text, re.I):
            flags.append("Check that the draft conveys " + fact)
    valid = {row["id"] for row in packet["sources"]}
    if set(re.findall(r"\bE\d{4}\b", text)) - valid:
        flags.append("The draft refers to an event outside the source packet")
    if re.search(r"https?://|\b[\w.+-]+@[\w.-]+\.[a-z]{2,}", text, re.I):
        flags.append("An external identifier appeared in the draft")
    if not text.strip() or len(text.split()) > 65 or not text.rstrip().endswith((".", "!", "?")):
        flags.append("Check for an incomplete or overlong response")
    return ("flagged" if flags else "requires review"), flags


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def snapshot(data, infer, runtime):
    cases = {}
    packets = source_packets(data)
    for case_id, packet in packets.items():
        drafts = {}
        for role in ROLES:
            prompt = messages(packet, role)
            answer = infer(prompt)
            status, flags = screen(answer, packet)
            drafts[role] = {"text": answer, "status": status, "flags": flags, "prompt_sha256": digest(prompt)}
        cases[case_id] = {**packet, "drafts": drafts}
    return {"schema_version": 1, "status": "ready", "model_id": MODEL, "revision": REVISION,
            "protocol": PROTOCOL, "input_sha256": digest(packets), "runtime": runtime, "cases": cases}


def validate(data, artifact):
    packets = source_packets(data)
    expected = {"schema_version": 1, "status": "ready", "model_id": MODEL, "revision": REVISION,
                "protocol": PROTOCOL, "input_sha256": digest(packets)}
    if any(artifact.get(key) != value for key, value in expected.items()):
        raise ValueError("Provenance does not match the generation protocol")
    if set(artifact["cases"]) != set(packets):
        raise ValueError("Missing case drafts")
    for case_id, packet in packets.items():
        case = artifact["cases"][case_id]
        if any(case.get(key) != value for key, value in packet.items()) or set(case["drafts"]) != set(ROLES):
            raise ValueError("Source text, role or scope changed")
        for role, item in case["drafts"].items():
            if not isinstance(item["text"], str) or item["prompt_sha256"] != digest(messages(packet, role)):
                raise ValueError("Draft prompt provenance changed")
            if (item["status"], item["flags"]) != screen(item["text"], packet):
                raise ValueError("Draft quality screen has been changed")


def cpu_generator():
    import torch
    import transformers
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch.manual_seed(0)
    torch.set_num_threads(min(4, torch.get_num_threads()))
    options = {"revision": REVISION, "trust_remote_code": False}
    tokenizer = AutoTokenizer.from_pretrained(MODEL, **options)
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float32, use_safetensors=True, **options).eval()
    token_limit = 80

    @torch.inference_mode()
    def infer(prompt):
        inputs = tokenizer.apply_chat_template(prompt, tokenize=True, add_generation_prompt=True,
                                               return_tensors="pt", return_dict=True)
        generated = model.generate(**inputs, do_sample=False, max_new_tokens=token_limit,
                                   pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(generated[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    return infer, {"engine": "PyTorch CPU", "torch": str(torch.__version__), "transformers": transformers.__version__,
                   "precision": "float32", "sampling": "greedy", "max_new_tokens": token_limit,
                   "workflow_run": os.environ.get("GITHUB_RUN_ID"), "source_commit": os.environ.get("GITHUB_SHA")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()
    data = read(INPUT)
    if args.validate:
        validate(data, read(args.output))
        return
    infer, runtime = cpu_generator()
    result = snapshot(data, infer, runtime)
    validate(data, result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(args.output)


if __name__ == "__main__":
    main()
