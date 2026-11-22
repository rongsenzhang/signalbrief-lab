# Reproducing version 1.0

Start in the repository root. The core checks run on Python 3.9+ with the standard library. GitHub Actions supplies a Python 3.11 Linux environment, Chromium and loopback networking for the interface tests.

| Release question | How to check it |
| --- | --- |
| Do the same cases produce the same decisions after a fresh build? | Run `python3 scripts/build_demo.py` and `python3 scripts/contract_examples.py`, then compare both published JSON files with Git. |
| Does the authenticated service return the same evidence as the workbench? | Run `python3 -m unittest discover -s tests -v`. The suite compares every published frame with the wire-format handler, exercises the local socket when permitted and tests the 15/16-minute branch. |
| How does the router behave outside its synthetic vocabulary? | Run `python3 scripts/corpus_check.py --check`. It checks the upstream file identity, recomputes coverage and compares the result with [the public aggregate](../reference/corpus-check.json). |
| Can a reviewer use the whole product? | The [release workflow](https://github.com/rongsenzhang/signalbrief-lab/actions/workflows/release-checks.yml) runs the workbench and integration smoke scripts with a desktop viewport and a mobile viewport. Review its log for the tested commit. |
| What did the language model actually return? | Open the [model run record](../docs/data/language-model.json), the [model card](../docs/model-card.md) and the [model workflow](https://github.com/rongsenzhang/signalbrief-lab/actions/workflows/model-snapshot.yml). Each generated choice is checked against the published case prefix. |
| How were the two audiences tested? | The [drafting workflow](https://github.com/rongsenzhang/signalbrief-lab/actions/workflows/handover-drafts.yml) preserves the raw text, source packet, prompt fingerprint and flags for each role. Compare a generated draft to its original record in the [draft experiment](../docs/data/handover-drafts.json). |
| How much work was timed? | The [benchmark](../docs/data/evaluation.json) repeats six scenario families with a warm single-process Python engine. Runtime includes rules, text routing and frame construction. It excludes HTTP, LLM inference and human review. |

The public page uses static records and lets visitors keep a handover in their own browser. A mobile viewport test covers a narrow layout and touch-sized controls under automation. Actual phones, operating system accessibility tools, customer data, the partner's in-house software and multi-tenant deployments require separate evaluation.
