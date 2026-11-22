# Run a seven-minute shift handover

**Audience:** A service-desk colleague and a trainer. Open the public workbench on a phone or laptop. The exercise uses the synthetic case **SB-101 · Unrecognised sign-in**. One person operates the workbench and the other plays the service owner.

| Time | Learner action | Trainer prompt |
| --- | --- | --- |
| 0–1 min | Open SB-101 and select **Restart replay**. Read the first entry in **Evidence ledger**. | “What do we know at this point? What would you need before calling this an incident?” |
| 1–3 min | Select **Next event** twice. At each step, name the source and explain what changed. Pause at the final event. | “Point to the evidence that makes this worth following up. Which question is still open?” |
| 3–4 min | Read both the analyst and service-owner versions of the case brief. Give a 20-second spoken update to the service owner. | “Explain the concern and your next step in language I can use. What could you safely tell a customer?” |
| 4–6 min | At the final event, choose a disposition and enter a reason. Select **Save review**, then **Download handover**. Read the exported text as if you were the next shift. | “Can the next colleague find your evidence and tell who needs to do what?” |
| 6–7 min | Swap roles. The service owner challenges one conclusion. Revisit the evidence and explain whether the handover needs a correction. | “Would the available evidence support telling a customer that their account was taken over?” |

## Trainer's answer key

1. **At the first event:** The gateway logged unsuccessful requests. This observation alone cannot establish who made them or whether anyone gained access.
2. **After the next two events:** The identity provider recorded an accepted session (E1012). A separate service-desk report says the user did not recognise it (E1013). Together they warrant a prompt identity review. A report still needs verification, and a successful sign-in does not identify the person who made it.
3. **Example spoken handover:** “Several sign-in requests were declined. A session was then accepted, and the account holder reported that they did not recognise it. Please check with them using our established contact route and record what they confirm.”
4. **Example decision:** Escalate to the identity team for independent confirmation. Cite the accepted session and the service-desk report. Include the failed requests if they help explain the sequence. A different disposition needs a clear owner, next step and reason grounded in the same evidence. The reviewer decides how the case proceeds.

## Sign-off and feedback

The trainer can sign off when the learner independently reconstructs the sequence, distinguishes the report from confirmed compromise, communicates the same facts to both audiences and exports a handover another colleague can act on. For independent practice, use SB-104, *Staff account access check*. Its first two observations resemble SB-101, but the third records that the owner recognises the session. Ask the learner to revise the handover using the changed evidence.

Record the exercise date, case ID, review outcome, one phrase that confused the learner and the criterion to revisit. A missed criterion becomes the starting point for the next practice case. Keep practice records within the training team.
