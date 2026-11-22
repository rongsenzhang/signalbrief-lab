"""Detect changes in review priority as normalised fictional observations arrive."""
import argparse
import json
import sys
from contextlib import nullcontext

from .api import unique_fields
from .engine import FIXTURES, RUBRIC, SCOPES, WINDOW_SECONDS, InvalidInput, parse_events, review_finding

MAX_LINE_BYTES = 1024


class CaseState:
    def __init__(self):
        self.seen = {}  # At most 10,000 canonical identifiers for each allowlisted scope.
        self.recent = {}  # One observation per signal, in acceptance order.
        self.watermark = None
        self.priority = None
        self.finding = None


class EventStream:
    def __init__(self):
        self.cases = {scope: CaseState() for scope in SCOPES}

    def ingest(self, packet):
        """Consume exactly one packet. A rejected or duplicate packet has no effect."""
        if not isinstance(packet, dict) or set(packet) != {"scope", "id", "time", "signal"}:
            return {"status": "rejected", "code": "schema"}
        scope = packet["scope"]
        row = {name: packet[name] for name in ("id", "time", "signal")}
        try:
            (instant, event), = parse_events(scope, [row])
        except InvalidInput:
            return {"status": "rejected", "code": "schema"}
        state = self.cases[scope]
        identity = {"scope": scope, "event_id": event["id"]}
        signature = (event["time"], event["signal"])
        if event["id"] in state.seen:
            if state.seen[event["id"]] == signature:
                return {"status": "duplicate", **identity}
            return {"status": "rejected", "code": "conflict", **identity}
        if state.watermark is not None and instant < state.watermark:
            return {"status": "rejected", "code": "late", **identity}

        # Every rubric consults the latest occurrence of a signal. Removing older
        # repeats preserves arrival order for same-second observations and sessions.
        recent = {code: observation for code, observation in state.recent.items()
                  if (instant - observation[0]).total_seconds() <= WINDOW_SECONDS}
        window = [observation for _, observation in recent.values()] + [event]
        rule, evidence, finding = review_finding(window, state.finding)
        priority, reason = RUBRIC[rule][:2]
        previous = state.priority
        transition = {"from": previous, "to": priority} if previous != priority else None
        recent.pop(event["signal"], None)
        recent[event["signal"]] = (instant, event)
        state.recent = recent
        state.seen[event["id"]] = signature
        state.watermark = instant
        state.finding = finding
        state.priority = priority
        return {"status": "accepted", **identity, "time": event["time"], "signal": event["signal"],
                "source": event["source"], "text": event["text"], "priority": priority,
                "previous_priority": previous, "transition": transition,
                "alert": priority == "High" and previous != "High",
                "rule": rule, "reason": reason, "evidence_ids": [item["id"] for item in evidence]}


def stream_results(source):
    """Consume a binary stream incrementally, including bounded reads for invalid lines."""
    detector = EventStream()
    while True:
        line = source.readline(MAX_LINE_BYTES + 1)
        if not line:
            return
        if len(line) > MAX_LINE_BYTES:
            while line and not line.endswith(b"\n"):
                line = source.readline(MAX_LINE_BYTES + 1)
            yield {"status": "rejected", "code": "line_too_long"}
            continue
        try:
            packet = json.loads(line.decode("utf-8"), object_pairs_hook=unique_fields)
        except (ValueError, RecursionError):
            yield {"status": "rejected", "code": "invalid_json"}
            continue
        yield detector.ingest(packet)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Read the bundled interleaved fictional packets.")
    args = parser.parse_args()
    input_stream = (FIXTURES / "stream-demo.ndjson").open("rb") if args.demo else nullcontext(sys.stdin.buffer)
    with input_stream as source:
        for result in stream_results(source):
            print(json.dumps(result, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
