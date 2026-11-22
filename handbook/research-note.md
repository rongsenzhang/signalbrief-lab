# Presenting uncertainty in an alert handover

**Talk outline for an eight-minute engineering or applied NLP session.** Which parts of a multi-source alert can a system explain faithfully to a service owner, and which decisions still need an analyst?

## Programme abstract

A disputed staff sign-in looks different to a duty analyst and the person responsible for service continuity. Both need an explanation that can be checked against the same observations. This demonstration follows one synthetic alert as new records arrive, shows how changing a single observation can alter the handover, and compares the brief with its supporting events. A separate language-model experiment asks which observation is most relevant. The session ends with a test a service team can run to find out whether an explanation saves time while preserving sound judgement.

## A case in three observations

Replay SB-101, *Unrecognised sign-in*. A gateway records declined requests. An identity provider then reports an accepted session. A service-desk report adds that the user does not recognise that session. At each stage, show the evidence available at that moment. Ask the audience when they would involve the identity team and what information they would request. The case ends with a reason to investigate. It offers no verified account of who signed in.

## What to show on stage

| Minutes | Demonstration | Question for the audience |
| --- | --- | --- |
| 0–2 | Show only the first observation. Ask for a one-sentence handover. | Which claim is the event sufficient to support? |
| 2–4 | Step through the subsequent observations. Compare the explanations for the two audiences. | Can the reader trace each material claim to the evidence visible at this point? |
| 4–6 | Open the evaluation and examine what was predicted, what was counted and the test population. | Which result would transfer to new data sources, vocabulary or class frequencies? |
| 6–8 | Export a reviewed handover. Ask a colleague to identify the unresolved fact and next owner. | What would you measure in a service pilot before adopting the workflow? |

## Reproducible evidence

Read the [machine-readable evaluation](../docs/data/evaluation.json) for the released measurements. Use its named task, tested sample sizes and metric definitions when reporting a result. The case replay is a worked example. Routing accuracy, evidence fidelity and time spent by an analyst answer different questions.

For the live discussion, open the mixed-topic probes in that evaluation. “The backup agent lost its heartbeat” was labelled *Telemetry* by the fixture author but routed to *Service continuity* by the model. The word “backup” identifies the service and the missing heartbeat describes a monitoring problem. Ask which team should own this handover and whether a second label would help. This diagnostic is reported separately from the held-out test.

The [external coverage check](../reference/corpus-check.json) adds 27 public OpenSSH message templates representing 2,000 records. The router assigned a topic to 17 templates (1,062 records) and abstained on 10 (938 records). The source has no human-assigned labels for our four topics. Coverage on this source cannot establish topic accuracy.

The role-specific briefs in the workbench come from the evidence rules. The separate [language-model run record](../docs/data/language-model.json) addresses a narrower research question. Given the evidence in a frame, which displayed observation does the model select? To assess it, compare the selection with independently labelled acceptable event IDs, include frames with no sufficient evidence and count abstentions. A valid event ID can still point to a poor choice of evidence.

## Proposed pilot hypotheses

| Hypothesis | Comparison and measure | Evidence that would change the design |
| --- | --- | --- |
| The brief helps a second analyst reconstruct the case. | Give reviewers either an event list or a brief plus its evidence. Counterbalance order across matched case pairs. Record completion time, correct source identifications and unsupported claims. | Faster reviews with more factual errors would justify revising the brief before scaling. |
| Audience adaptation preserves facts while improving comprehension. | Give service owners a generic or audience-specific brief. Ask them to identify the suspected issue, what remains unknown and who should act. Blind-score the responses against the available evidence. | Loss of uncertainty or an increase in unnecessary escalation would justify revising wording and repeating the test. |
| The routing model generalises across sources. | With agreed permissions, reserve an entire source and later time window for testing. Compare routing against a simple baseline on identical cases. Report per-class precision/recall, abstentions and errors on rare cases. | A weak class or a score collapse on a new source calls for more representative examples and a more conservative review rule. |

Use colleagues who did not author the cases for the comprehension pilot. Two raters should record disagreements on claim support, reconcile them against the source evidence and preserve the original ratings. Keep the business outcome measurable by separating model runtime from human minutes per completed handover.

## Limits and communication

The release uses synthetic events. It demonstrates the reasoning and integration workflow; its benchmark cannot estimate the frequency of real incidents, missed threats on a customer network, staff time saved or commercial return. A model's language can sound more certain than the evidence permits. Keep the original event and the analyst's disposition accessible.

For external dissemination, publish the task, synthetic fixtures, versioned results and failure examples. Obtain partner agreement before including customer-specific findings in an industry presentation or paper. This note is a proposed talk and evaluation protocol.
