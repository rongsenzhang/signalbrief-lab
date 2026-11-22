# Model card · Evidence selection

SignalBrief uses a small, open-weight instruction model to select one observed event for a service handover. The analyst can read its original wording and compare it with the brief. The routing classifier, escalation policy and role-specific briefs run independently of this model.

## What goes in and what comes out

The prompt contains the **current finding**, synthetic event sources and event text available by the selected replay step. A frozen chat instruction asks the model to choose a letter or abstain. The same question runs again with the candidates reversed. One-candidate frames require one inference. Answers outside the available letters, abstentions and disagreement return no selection. A consistent choice is resolved to its original event ID and **verbatim** text. Model output never commands a security tool or changes a review decision.

| Component | Implementation |
| --- | --- |
| Model | HuggingFaceTB/SmolLM2-135M-Instruct, Apache-2.0 |
| Revision | `12fd25f77366fa6b3b4b768ec3050bf629380bac` |
| Public browser lab | Explicit download, Transformers.js 3.8.1, int8 ONNX via single-thread WASM, greedy decoding |
| Reproducible snapshot | Transformers 4.51.3, PyTorch 2.6.0 CPU, float32, greedy decoding, four output tokens maximum |
| Shared prompt | `docs/model/protocol.json` |
| Source provenance | The snapshot contains the replay file SHA-256, model revision, runtime versions, raw answers and per-frame outcomes |
| External traffic | The optional browser lab downloads code and weights when requested. Inference uses synthetic data locally. The reviewer’s notes are outside its input. Hosting and download providers receive ordinary web requests. |

Weights, architecture and model licence are documented by Hugging Face. [Model and weights](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/tree/12fd25f77366fa6b3b4b768ec3050bf629380bac) · [ONNX variants and sizes](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct/tree/12fd25f77366fa6b3b4b768ec3050bf629380bac/onnx)

## Run and inspect

From the repository root, use a Python 3.11 environment with internet access. The snapshot workflow installs the CPU PyTorch wheel on its Linux runner. The commands below also run on a supported desktop Python installation.

```sh
python -m pip install torch==2.6.0 transformers==4.51.3
python scripts/llm_evidence.py --output build/language-model.json
python scripts/llm_evidence.py --validate --output build/language-model.json
```

The [successful workflow](https://github.com/rongsenzhang/signalbrief-lab/actions/runs/45082386719) ran both CPU and in-browser inference. It can be started manually or by a relevant push to main. Open its `language-model-snapshot` artifact for the full JSON. A verified artifact can replace `docs/data/language-model.json` for small-device access. The value of `status` in the public file distinguishes a published run from an unexecuted snapshot. The browser lab runs independently of any saved result. Int8 inference may select a different record from the float32 workflow.

## Observed release result

On the 17 published prefixes, SmolLM2 returned no usable selection: 14 outputs had an invalid format or choice and three abstained. On the 11 multi-event prefixes, selecting the newest event agreed with the rule citations on 10. The policy evidence and original events remain the source of the operational handover. In a separate real Chromium run on SB-101, step 3, the int8 model also returned text outside the permitted answers. The interface exposed the raw output and showed no selected source. [CPU results](data/language-model.json) · [CPU and browser run](https://github.com/rongsenzhang/signalbrief-lab/actions/runs/45082386719)

The drafting and routing experiments use Qwen2.5-0.5B-Instruct and answer different questions. [Handover quality](https://github.com/rongsenzhang/signalbrief-lab/blob/main/handbook/draft-method.md) · [Label-restricted topic routing](https://github.com/rongsenzhang/signalbrief-lab/blob/main/handbook/llm-routing.md)

## How to interpret evaluation

For multi-event frames, `multi_event_matches` counts selections that appear among the deterministic policy's supporting evidence IDs. `most_recent_matches` counts the same for the latest observation. Both share the denominator `multi_event_frames`, including model abstentions. `multi_event_selected` measures coverage and makes the abstention cost visible. Single-event frames are reported separately through the total counts. The selected event can support only one part of a multi-source finding.

These are agreement checks against a small synthetic policy reference. The fixtures reuse event structures across time and across cases. They cannot estimate real incident accuracy, hallucination rates on arbitrary input or the accuracy of the policy itself. Occupying the same position twice can favour a letter, and agreement under reversal is only one check for positional bias. Before deployment, ask independent analysts to label ambiguous cases, score preference against a recency baseline on held-out services, and measure end-to-end handover quality. Public source code and tests alone do not establish that a model run occurred.
