# SignalBrief Lab

A security service desk receives three reports. A gateway rejected sign-in attempts, the identity provider accepted a session, and the account holder says they do not recognise it. At what point should an analyst escalate? What can the next shift tell the service owner with confidence?

**[Open the interactive workbench](https://rongsenzhang.github.io/signalbrief-lab/)** · [Change the evidence in the integration lab](https://rongsenzhang.github.io/signalbrief-lab/integration.html) · [Technical design](handbook/architecture.md) · [Model card](docs/model-card.md) · [Qwen vs the fitted classifier](handbook/llm-routing.md) · [API contract](reference/api.md)

SignalBrief is an independent ML/NLP application prototype by Rongsen Zhang for the University of Essex and Centerprise International KTP, REQ10407. All case data is fictional. The prototype implements its own interface and has no access to Centerprise products or customer systems.

## A two-minute review

1. Open **SB-101 · Unrecognised sign-in**. Advance one event at a time. Watch the evidence ledger and the priority as the account holder's report arrives.
2. Switch from **Analyst** to **Service owner**. Follow a supporting event, then read the open question. The evidence justifies an investigation. It cannot identify who opened the session.
3. Save a disposition and download the handover. Compare **SB-104 · Staff account access check**, which starts with similar signals and ends differently.
4. At the final event, open **Compare model draft**. Switch audiences. Compare the original Qwen wording with the observations and the case-specific review. In SB-106 the model describes the monitoring gap as resolved, although the source only says collection resumed.
5. In the **API lab**, change a disputed sign-in from 15 to 16 minutes. Then replay the interleaved event stream to see when a new alert first appears.
6. Inspect the model evidence and [evaluation record](docs/data/evaluation.json). Pay attention to abstentions and to the baseline. A valid citation can still be a poor explanation.

## Inside the release

| Component | What runs |
| --- | --- |
| Event processing | A [Python stream adapter](reference/stream.md) accepts interleaved synthetic observations one line at a time, correlates independent sources and emits an alert on entry to High. The browser lab can replay a captured trace or read decisions as they arrive from a local HTTP stream. |
| Text routing | A fitted multinomial naïve Bayes classifier predicts the topic. Its score refers to the routing decision. It does not estimate the probability of a compromise. |
| Handover drafting | A pinned Qwen2.5-0.5B-Instruct experiment drafts an analyst update and a service-owner update from the final evidence packet. Inspect the [draft method](handbook/draft-method.md) and [run record](docs/data/handover-drafts.json) for the raw outputs, flags and review status. |
| Evidence selection | A pinned SmolLM2-135M-Instruct model selects an observation for a finding. Compare two candidate orderings, preserve the raw choices and abstain on disagreement. The model card identifies the execution modes and their limits. |
| Public workbench | A responsive static site replays the same Python-generated frames used by the integration contract. It switches brief audience, records a local review and exports evidence. No account or API key is needed to review a case. |
| Python HTTP API | A bounded, bearer-authenticated local endpoint accepts synthetic event codes and computes new frames. The public lab lets a reviewer change the account holder’s report and its timing across ten API examples. The same page can make authenticated POST requests to the local Python service. |
| Evaluation | Held-out language families test text routing. A separate synthetic stream benchmark measures processing throughput. An [external OpenSSH corpus check](reference/corpus-check.json) measures routing coverage on a separate source. Only the synthetic routing test has author-assigned topic labels. |

## Reproduce

The core engine, API and unit tests use the Python standard library. From the repository root:

```sh
python3 scripts/build_demo.py
python3 scripts/contract_examples.py
python3 scripts/build_stream_trace.py
python3 -m unittest discover -s tests -v
python3 -m http.server 8000 --bind 127.0.0.1 --directory docs
```

Open [localhost:8000](http://localhost:8000/). See the [API contract](reference/api.md) for an authenticated request and the [model card](docs/model-card.md) for the separate model runtime and snapshot validation. Rebuilding the cases should reproduce the committed scenario JSON.

## Research, delivery and knowledge transfer

| Reader | Starting point |
| --- | --- |
| Hiring panel | [Seven duties mapped to evidence, pilot milestones and costing](handbook/role-mapping.md) |
| Service lead | [Funded KTP and engineering priorities](handbook/ktp-evidence.md) · [Centerprise services and competitors](handbook/company-and-market.md) · [How a service desk handles a recovery case](handbook/service-workflow.md) |
| Engineer | [Architecture and integration choices](handbook/architecture.md) · [API contract](reference/api.md) |
| Trainer | [Seven-minute service-desk workshop with answer key](handbook/workshop.md) |
| Research supervisor | [Talk outline and evaluation design](handbook/research-note.md) · [Release verification](handbook/verification.md) |

The design gives analysts control of the handover. Deploying inside a managed service would require a partner-approved source mapping, identity and access model, incident procedure, independent evaluation on representative data and staff training.
