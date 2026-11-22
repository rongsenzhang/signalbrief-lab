"""Evidence-first triage of one synthetic subject's ordered event stream."""
import json
import re
from datetime import datetime, timezone
from .model import FIXTURES, router

with (FIXTURES / "signals.json").open() as file:
    SIGNALS = json.load(file)
SCOPES = {
    "ACCESS-A": {"access_declined", "session_opened", "owner_disputes", "owner_confirms"},
    "DEVICE-A": {"endpoint_block", "endpoint_note", "process_observed"},
    "BACKUP-A": {"backup_late", "restore_pending", "restore_verified"},
    "FEED-A": {"monitor_gap", "vague_notice", "feed_resumed"},
}
MAX_EVENTS = 32
WINDOW_SECONDS = 900


class InvalidInput(ValueError):
    """Safe to return to a caller. Messages never carry submitted values."""


def parse_events(scope, events):
    if not isinstance(scope, str) or scope not in SCOPES:
        raise InvalidInput("Choose a scope from the integration contract.")
    if not isinstance(events, list) or not 1 <= len(events) <= MAX_EVENTS:
        raise InvalidInput("A case must contain 1 to 32 events.")
    seen, previous, parsed = set(), None, []
    for row in events:
        if not isinstance(row, dict) or set(row) != {"id", "time", "signal"}:
            raise InvalidInput("Each event requires exactly id, time and signal.")
        eid, timestamp, signal = row["id"], row["time"], row["signal"]
        if not isinstance(eid, str) or re.fullmatch(r"E[0-9]{4}", eid) is None or eid in seen:
            raise InvalidInput("Event IDs must be unique and have the form E1234.")
        if not isinstance(timestamp, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", timestamp):
            raise InvalidInput("Timestamps require UTC, whole seconds and a trailing Z.")
        try:
            instant = datetime.fromisoformat(timestamp[:-1]).replace(tzinfo=timezone.utc)
        except ValueError:
            raise InvalidInput("Invalid calendar date or time.") from None
        if previous is not None and instant < previous:
            raise InvalidInput("Events must appear in timestamp order.")
        if not isinstance(signal, str) or signal not in SCOPES[scope]:
            raise InvalidInput("Signal must belong to the supplied scope.")
        source, text = SIGNALS[signal]
        parsed.append((instant, {"id": eid, "time": timestamp, "source": source, "text": text, "signal": signal}))
        previous = instant
        seen.add(eid)
    return parsed


# Rules describe observable outcomes. Independent confirmation applies only inside one scope.
# priority, explanation, plain-language interpretation, open question, suggested human task
RUBRIC = {
    "identity_high": (
        "High", "The identity provider recorded a new session and the account owner independently disputed it.",
        "Someone may have used the account without the owner's knowledge.",
        "Who opened the session and what they accessed remain unknown.",
        "Verify the report with the account owner through a known contact route and refer it to the duty analyst."),
    "identity_conflict": (
        "High", "The identity provider recorded a session. Service-desk reports disagree on whether the owner recognised it.",
        "The team has received two different accounts of the same sign-in.",
        "The conflicting reports leave the identity of the person who opened the session unresolved.",
        "Ask the duty analyst to reconcile both reports with the owner using a known contact route."),
    "identity_recognised": (
        "Routine", "The account owner recognised the session recorded by the identity provider.",
        "The owner confirmed the access they were asked about.",
        "The confirmation covers this session only.",
        "Record the owner's confirmation and review any other access alerts separately."),
    "identity_two": (
        "Review", "Rejected requests preceded a new session for this account.",
        "A new session followed several unsuccessful attempts. The owner's involvement needs checking.",
        "The records do not identify who opened the session.",
        "Check the session with the account owner through a known contact route."),
    "identity_one": (
        "Review", "The available access evidence does not meet a corroboration rule.",
        "An account access event needs context.",
        "The evidence does not establish whether the access was expected.",
        "Check the identity-provider record and seek independent confirmation."),
    "endpoint_high": (
        "High", "Independent inventory observed the same running process after endpoint protection recorded a block.",
        "A device may still be running an application that its protection tried to stop.",
        "Application intent and impact on the device remain unknown.",
        "Pass both records to the endpoint analyst to verify the device's current state."),
    "endpoint_review": (
        "Review", "The endpoint evidence has no independent confirmation of continued activity.",
        "A device alert needs an independent check.",
        "The available record does not establish a persistent problem.",
        "Compare the protection record with a separate inventory observation."),
    "backup_late": (
        "Review", "The backup scheduler reported a missed recovery window.",
        "The latest recovery copy may be late.",
        "Recoverability for this window has not been verified.",
        "Ask the recovery owner for the result of a restore check."),
    "backup_pending": (
        "Review", "A restore result is still pending for the delayed copy.",
        "The service team is waiting for evidence that the copy is usable.",
        "The missing result does not establish that data was lost.",
        "Track the outstanding restore verification with the recovery owner."),
    "backup_verified": (
        "Routine", "An independent restore exercise verified a usable copy for the reported window.",
        "The service team has confirmed it can recover the tested copy.",
        "The exercise covers the tested copy only.",
        "Attach the verification result and record the scheduling delay."),
    "feed_gap": (
        "Review", "The monitor reported a gap in collection.",
        "Part of the service record is missing.",
        "The missing interval cannot establish what happened during it.",
        "Ask the monitoring owner to check coverage during the missing interval."),
    "feed_return": (
        "Review", "The feed resumed after a recorded gap. Resumption does not fill the missing interval.",
        "Monitoring is back, but the team still lacks part of the record.",
        "Events during the gap remain unknown.",
        "Record the coverage gap and ask whether the missing interval can be reconciled."),
    "unclear": (
        "Review", "There is too little corroborated evidence for a stronger decision.",
        "The service team needs more detail before drawing a conclusion.",
        "The available observation does not establish cause or impact.",
        "Request a second, independently sourced observation.")
}


def decide(window):
    last = window[-1]
    code = last["signal"]
    previous = {row["signal"]: row for row in window[:-1]}
    if code in {"owner_confirms", "owner_disputes"} and "session_opened" in previous:
        session = previous["session_opened"]
        opposite = "owner_confirms" if code == "owner_disputes" else "owner_disputes"
        # Report arrival order is meaningful even when two timestamps coincide.
        since_session = window[window.index(session) + 1:-1]
        conflicting = next((row for row in reversed(since_session) if row["signal"] == opposite), None)
        if conflicting is not None:
            return "identity_conflict", [session, conflicting, last]
        key = "identity_high" if code == "owner_disputes" else "identity_recognised"
        return key, [session, last]
    if code == "session_opened" and "access_declined" in previous:
        return "identity_two", [previous["access_declined"], last]
    if code in SCOPES["ACCESS-A"]:
        return "identity_one", [last]
    if code == "process_observed" and "endpoint_block" in previous:
        return "endpoint_high", [previous["endpoint_block"], last]
    if code in SCOPES["DEVICE-A"]:
        return "endpoint_review", [last]
    if code == "backup_late":
        return "backup_late", [last]
    if code == "restore_pending" and "backup_late" in previous:
        return "backup_pending", [previous["backup_late"], last]
    if code == "restore_verified" and "backup_late" in previous:
        return "backup_verified", [previous["backup_late"], last]
    if code == "monitor_gap" or (code == "vague_notice" and "monitor_gap" in previous):
        return "feed_gap", [previous.get("monitor_gap", last)] if code == "vague_notice" else [last]
    if code == "feed_resumed" and "monitor_gap" in previous:
        return "feed_return", [previous["monitor_gap"], last]
    return "unclear", [last]


def triage(scope, rows):
    events, frames, persistent = [], [], None
    parsed = parse_events(scope, rows)
    window = []
    for instant, event in parsed:
        window = [(t, row) for t, row in window if (instant - t).total_seconds() <= WINDOW_SECONDS]
        window.append((instant, event))
        events.append(event)
        key, evidence = decide([row for _, row in window])
        if persistent is not None:
            # Preserve a human review gate while including newer contradictory evidence
            # only when the two findings concern the same synthetic session.
            if key == "identity_conflict" and evidence[0]["id"] == persistent[1][0]["id"]:
                persistent = key, evidence
            key, evidence = persistent
        elif RUBRIC[key][0] == "High":
            persistent = key, evidence
        priority, reason, manager, unknown, next_step = RUBRIC[key]
        model = router().predict(event["text"])
        evidence_ids = [row["id"] for row in evidence]
        analyst = " ".join(f'{row["text"]} [{row["id"]}]' for row in evidence)
        frames.append({"event_ids": [row["id"] for row in events], "category": model["label"],
                       "priority": priority, "reason": reason, "analyst": analyst, "manager": manager,
                       "unknown": unknown, "next_step": next_step, "evidence_ids": evidence_ids,
                       "model": model, "rule": key})
    return {"events": events, "frames": frames}
