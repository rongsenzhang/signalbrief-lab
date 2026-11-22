# Reviewing an LLM handover

A service owner needs to understand what happened to a service. A duty analyst needs the observations that support that account. This experiment asks one model to write for each reader using the same bounded evidence. The results appear on request at the end of each case. A reviewer can read both drafts alongside the original evidence. The analyst's decision and the service-owner brief in the workbench come from the separate, reproducible case engine.

## What the model saw

Each input contains just the final decision's cited synthetic observations, their IDs and sources, and the case engine's statement of what remains unknown. There are six source packets and two audiences per packet. The generator checks every observation against the repository's synthetic signal catalogue. The role instruction changes while the available facts stay fixed. The target brief, severity and recommended action are excluded.

## What the snapshot records

The generator uses Qwen2.5-0.5B-Instruct with a frozen model and tokenizer, CPU float32, greedy decoding and an 80-new-token limit. The JSON retains the actual decoded completion for each role alongside its source packet, prompt hash, runtime, model revision, input hash and, on GitHub Actions, source commit and run ID. A pending snapshot contains no drafts. Fixed settings allow replication and numerical differences across runtime or processor builds remain possible. [Pinned model](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct/tree/7ae557604adf67be50417f59c2c2f167def9a775) · [Draft snapshot](../docs/data/handover-drafts.json) · [Generator and screening rules](../scripts/handover_drafts.py) · [Inference runs](https://github.com/rongsenzhang/signalbrief-lab/actions/workflows/handover-drafts.yml)

## How to assess a draft

1. Underline each factual claim in the draft and identify the observation or stated evidence limit that supports it.
2. Check the sequence and attribution. An account owner's report and a system observation support different claims. A recovery exercise covers the copy that was tested.
3. Check polarity and scope. Distinguish a delayed result from a failed restore, a missing interval from missing business data, and unexpected sign-in from proven compromise.
4. Inspect omissions and wording for the intended audience. A supported statement can still omit the uncertainty that the next shift needs.
5. Give the writer a concrete correction and cite the evidence IDs. The product does not automatically promote any draft into a case decision.

The automated screen flags selected overclaims, possible reversals, missing expected concepts, new references and length problems. Text with no matching flag receives **requires review**. These lexical checks can miss unsupported claims and can over-flag negated or qualified statements. A model response of **ABSTAIN** is recorded separately. The twelve outputs share six authored scenarios. They do not establish a population error rate or performance on customer reports.

## Worked reviewer checks

The following deliberately constructed examples exercise the verification logic. The recorded model outputs are in the linked snapshot.

| Case | Illustrative draft claim | Evidence check |
| --- | --- | --- |
| Unrecognised sign-in | “The account was compromised.” | E1012 records a session and E1013 reports the owner's dispute. Neither establishes the identity of the person who opened it. |
| Recovery window review | “The delayed backup was verified.” | E1031 records a missed window and E1032 says the check has no result. The completion claim reverses the outstanding status. |
| Monitoring coverage | “The feed resumed and the gap was filled.” | E1061 records missing telemetry. E1063 shows collection restarting, with the missing interval unresolved. |

## Reproduce

Use Python 3.11 with CPU PyTorch 2.6.0 and Transformers 4.51.3. The initial run downloads the pinned open weights. From the repository root, run `python scripts/handover_drafts.py --output build/handover-drafts.json`. Verify the file without model dependencies with `python scripts/handover_drafts.py --validate --output build/handover-drafts.json`. Each workflow run publishes its output as the artifact named `handover-drafts`.
