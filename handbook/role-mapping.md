# From the KTP brief to an assessable prototype

This independent application project translates the University of Essex and Centerprise International brief into a small, reviewable workflow. A reviewer can follow an alert, inspect its sources, explain it to a service owner and record a handover. The public fixture represents a possible integration boundary. The partner's software contract, operating procedures and data remain unknown.

## The appointment

Essex lists REQ10407 as a 25-month, 40-hour-per-week KTP Associate post paying £41,000–£45,000. Tuesday to Thursday are based at Centerprise in Basingstoke. Monday and Friday are remote, with occasional travel to Colchester. The advertised closing date is 3 December 2026. Shortlisting uses the online application, a CV and a covering letter with examples against the person specification. The job pack also gives the right-to-work and government-contract vetting conditions. [Essex recruitment page and job pack](https://vacancies.essex.ac.uk/tlive_webrecruitment/wrd/run/ETREC107GF.open?VACANCY_ID=208360f0kv&WVID=9918109NEm&LANG=USA)

## Seven duties and the acceptance test for each

| Duty in practical terms | Evidence to inspect | What a reviewer can check |
| --- | --- | --- |
| Introduce an LLM into an existing security workflow | [Evidence selection](../docs/model-card.md), [handover drafting](draft-method.md) and [raw draft results](../docs/data/handover-drafts.json) | Inspect the model revision, inference mode and allowed answers. Inspect an evidence choice and a generated handover for different audiences. Compare the text with the original observations and the known limits. Decision authority remains with the analyst. |
| Simplify security work and an internal process | Case replay, audience briefs and handover export | Follow one case through to a shift handover. For a distinct operational workflow, compare SB-103 (a restore check is outstanding) with SB-105 (the recovery team has verified a usable copy). Record the next owner and check in the service-desk handover. |
| Deliver an interface and an integration API | Browser workbench and [HTTP contract](../reference/api.md) | Run the local authenticated endpoint. Compare the result for a documented case frame with the workbench at the same evidence state. The contract describes the prototype interface; integration would require a partner-approved adapter. |
| Help scale and exploit the technology | [Evaluation](../docs/data/evaluation.json) and pilot plan below | Inspect the population behind each measurement. Compare cost per reviewed case with the existing service process during a pilot. |
| Lead delivery against milestones | Milestones, owners and decision gates below | Follow the sequence from source mapping through validation and handover. Each proposed pilot gate has an owner and an observable completion condition. |
| Embed skills with company staff | [Seven-minute workshop](workshop.md) | Ask a colleague to complete the exercise independently and explain the escalation. Record the missed criteria and rerun them during handover. |
| Communicate research to academic and industry audiences | [Technical talk and research note](research-note.md) | Reproduce the reported evaluation and identify a claim that requires an external pilot. The talk outline gives a team a starting point for presentation and feedback. |

## Person specification and evidence limits

| Requirement group | Relevant material | Evidence still needed from the applicant or partner |
| --- | --- | --- |
| Related BSc and relevant MSc or equivalent industry experience | The application provides degree and employment records. A relevant doctorate, near-completion or equivalent experience is desirable. | Qualifications and employment history belong in the CV and supporting letter. |
| Programming, Python NLP and modern deep learning | [Python source](../src/signalbrief/), [model method](../docs/model-card.md) and [inference status](../docs/data/language-model.json). Inspect routing, structured evidence and the bounded language-model task separately. | Real-world LLM application experience requires a concrete account of a deployed use case, users, candidate contribution and outcome. |
| Large datasets, privacy, authentication and secure software design | [Evaluation](../docs/data/evaluation.json) and [API contract](../reference/api.md). Synthetic inputs and an access-controlled local API permit review without exposing customer telemetry. | Provide prior dataset sizes and processing constraints where substantiated. Production use needs agreed collection purposes, access roles, retention, hosting and review of transfers before any customer data is processed. |
| Problem solving, creative reasoning, verbal and written English, technical writing | Run the timed workshop, explain a disputed decision and use the talk protocol to defend the evaluation. | The panel can assess live explanation, listening and responses to feedback. Prior publications and conference drafting are separately desirable. |
| Client relationships, teamwork, commercial judgement and competing priorities | The workshop and pilot identify who reviews cases, who owns decisions, what to measure and when to stop. | Describe an actual stakeholder disagreement or delivery trade-off and its outcome. Commercial team experience, project management and budget ownership are desirable. |

The partner and university retain responsibility for hiring eligibility and checks. The [Essex vacancy and attached person specification](https://vacancies.essex.ac.uk/tlive_webrecruitment/wrd/run/ETREC107GF.open?VACANCY_ID=208360f0kv&WVID=9918109NEm&LANG=USA) give the full criteria. The [academic supervisor’s Essex profile](https://www.essex.ac.uk/people/SHEKH52208/ravi-shekhar) records the funded research objective.

## Version 1.0 delivery record

| Milestone | Evidence available to a reviewer | Decision |
| --- | --- | --- |
| Scope one service workflow | [Company analysis](company-and-market.md), [design](architecture.md) and six fictional scenarios | Selected shift handover and recovery assurance so both a service owner and a technical analyst can test the outcome. |
| Make the decision reproducible | [Core engine](../src/signalbrief/engine.py), [tests](../tests/) and [ten paired API examples](../docs/data/contract-examples.json) | The same function serves the authenticated API and builds the public decision examples. |
| Evaluate transfer beyond authored cases | [External coverage](../reference/corpus-check.json), [held-out examples and mixed-topic probes](../docs/data/evaluation.json) | Preserve abstentions and publish a mixed-topic error. The independent service team would need to supply labelled evaluation data. |
| Give another colleague a repeatable handover | [Workshop](workshop.md), [talk](research-note.md), [verification guide](verification.md) and [version history](https://github.com/rongsenzhang/signalbrief-lab/commits/main/) | Ship an exercise and checkable outputs alongside the application. A partner-led pilot is a separate stage. |

## Proposed pilot delivery

The owners and gates below are planning assumptions for a future trial. A team can review the public demonstration today without committing a customer, system or budget.

| Gate | Proposed owner | Exit evidence |
| --- | --- | --- |
| Define the service decision | Associate and service owner | Agree one handover workflow, define what counts as a completed review and record baseline sampling rules. |
| Map one source | Source owner and engineer | Agree event identifiers, timestamps and allowed fields. Check duplicates, missing fields and late events. Obtain approval for a permissible test dataset. |
| Evaluate in read-only shadow mode | Associate and analyst lead | Compare the current and proposed workflow on the same case mix. Review all unsupported claims, discarded events and missed escalations. Keep existing service decisions authoritative. |
| Train and hand over | Trainer and shift lead | A second analyst can reconstruct the review and repeat the exercise. The service owner records unresolved defects, rollback owner and support contact. |
| Extend, revise or stop | Service owner and commercial lead | Review evidence quality, analyst time, support burden and incremental hosting cost. Agree the acceptance threshold before evaluating another customer or source. |

**Illustrative pilot cost in GBP.** Two analysts at two hours each and £40/hour would cost £160. Fifteen engineering hours at £60/hour would cost £900. Two hours of privacy or service-owner input at £75/hour would add £150. With an assumed £40 hosting allowance, the planning total is **£1,250**. These are example inputs for a small evaluation, independent of the employer's budget. The estimate excludes procurement, integration with customer systems and production support.

For each new source, version the schema mapping, retain a de-identified contract fixture and rerun the held-out evaluation. Before a wider rollout, estimate monthly value from eligible reviews multiplied by *observed* time saved and loaded staff cost, less ongoing inference, hosting and support. Record analyst rework and erroneous escalations alongside time savings. If the service owner cannot reproduce the effect, retain the existing workflow and investigate the difference.
