# Technical design · SignalBrief Lab 1.0

## Reviewer journey

A duty analyst receives an alert about access to a service. With only the first event, the next decision may be to ask for context. A later event can corroborate the concern or explain it as an expected change. The service owner needs a brief that separates the observation, its possible operational impact and the question still open. The analyst decides how to hand it over.

The acceptance test starts at the first event. Step forward, watch the decision change, open its cited events, switch audience, record a disposition and export the handover. Repeat with a benign or inconclusive case. The public experience should work in a narrow mobile viewport and without credentials.

## Components and interfaces

| Step | Implementation choice | Acceptance evidence |
| --- | --- | --- |
| Ingest | Catalogue of synthetic signal codes with timestamp and event identifiers. A case groups related observations. | Reject malformed or extra fields. Avoid carrying raw user or customer data into a brief. |
| Replay | Build one snapshot for each prefix of a scenario. Preserve event order and evidence identifiers. | A frame can only cite events visible up to its timestamp. |
| Route | Train a small text classifier on labelled examples. Keep its routing score separate from the incident decision. | Held-out phrasing evaluation and confusion counts. |
| Prioritise | Apply explicit time and corroboration rules. Record the reason, uncertainties and next question. | A correlated sequence can reach High. A benign change or an isolated signal has a different outcome. |
| Explain | Assemble audience-specific summaries from observed facts. A separate language-model experiment selects supporting evidence. | Each cited identifier resolves. Model, inference mode and limits are visible. |
| Review | Let a reviewer step through the case, inspect evidence and record a decision. | Local review and export exercise on desktop and mobile. |
| Integrate | Serve the same Python triage logic behind a local authenticated HTTP interface. Publish precomputed fixtures for the static site. | Contract tests for authorised, unauthorised and invalid requests. |
| Evaluate and transfer | Keep wording quality, evidence selection, scale and user performance as distinct questions. | Machine-readable results, training exercise, integration guidance and pilot criteria. |

## Deployment boundaries

The public site serves static assets. It reads precomputed snapshots produced by the same engine used by the Python API. The API can be run separately for integration review. Connecting a live tenant would require agreement on field meanings, timestamp guarantees, event correlation keys, permitted data, error handling, retention, identity and operator permissions. The public project uses an independent schema.

A deployment partner would first implement a read-only adapter to the agreed event model. Use a signed-off replay dataset to test that late, duplicate and reordered events do not change a decision unexpectedly. Agree how missing signals and legitimate changes are represented. In shadow mode, compare analyst outcomes with and without the tool before enabling any downstream ticket creation.

## Research and commercial decisions

**First comparison.** Does a short audience-specific brief with links to observations reduce time to a correct escalation? Counterbalance the order of two unfamiliar cases. Capture decision correctness, unsupported claims, evidence lookup time and the handling of benign cases. A quicker incorrect escalation counts as a failure.

**Scale.** Report generator workload, hardware, elapsed time and scope alongside throughput. A synthetic local benchmark does not measure production alert diversity, concurrent tenants or end-to-end detection latency.

**Operational cost.** Static reviewer access has no inference charge to the applicant. A pilot must separately measure integration effort, infrastructure, model runtime, monitoring and analyst review time. Compare an extractive baseline with model-assisted evidence selection on incremental value per case.

**Privacy.** Limiting the public input vocabulary avoids processing arbitrary log text. Analyst decisions remain under human control. A production deployment would need a documented purpose, lawful handling arrangements, access review, retention policy and customer approval for its actual data flows. [ICO guidance on data minimisation](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/data-protection-principles/a-guide-to-the-data-protection-principles/data-minimisation/)

## Release gates

1. Rebuild the published snapshots and verify the committed artefacts.
2. Run deterministic engine, API and evidence-reference checks.
3. Reproduce the benchmark independently of browser rendering.
4. Check narrow and wide layouts and the full replay-to-export path.
5. Confirm the public source and website URLs from a reviewer’s perspective before adding them to an application.

## A decision at the integration boundary

Use the [integration lab](https://rongsenzhang.github.io/signalbrief-lab/integration.html) to change the second observation after a recorded session. The account holder can recognise or dispute the session at one of five elapsed times. The browser shows the exact requested records, the returned frame, its evidence and the next human check. For a disputed session at 15 minutes, both observations fall within the example policy window. At 16 minutes only the later observation supports the decision. This 15-minute limit is a prototype policy choice. A service owner would need to validate it against the timestamps, delays and subject identifiers of the intended source.

The published examples come from calling the actual Python API parser on ten different inputs. The same page runs against the authenticated HTTP service on a laptop. In local mode it sends a fresh POST and displays its actual HTTP result. The public site accepts no credentials. See the [integration contract](../reference/api.md) for setup.
