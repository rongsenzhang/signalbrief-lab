# Detecting a priority change as observations arrive

An identity-provider session on its own opens a review. When a separate service-desk report disputes that session within 15 minutes, the Python detector immediately emits a High transition citing both observations. An account holder who recognises their session produces a Routine decision. The change is evaluated when the record arrives. A reviewer can inspect the resulting evidence before preparing a handover.

## Run the detector

From the repository root, use Python 3.9 or newer. Each input line contains one JSON packet and each output line contains its result. The process flushes each result immediately. The second command accepts packets interactively or from another local process.

```sh
PYTHONPATH=src python3 -m signalbrief.stream --demo
PYTHONPATH=src python3 -m signalbrief.stream
```

For the interactive command, paste one line at a time. The first packet opens the review. The second packet triggers the alert. On a Unix terminal, Ctrl+D ends the stream.

```jsonl
{"scope":"ACCESS-A","id":"E7001","time":"2026-11-16T09:00:00Z","signal":"session_opened"}
{"scope":"ACCESS-A","id":"E7002","time":"2026-11-16T09:15:00Z","signal":"owner_disputes"}
```

The second result includes these fields. The full record also contains the observation and its catalogue source.

```json
{
  "status": "accepted",
  "scope": "ACCESS-A",
  "event_id": "E7002",
  "previous_priority": "Review",
  "priority": "High",
  "transition": {"from": "Review", "to": "High"},
  "alert": true,
  "rule": "identity_high",
  "evidence_ids": ["E7001", "E7002"]
}
```

The bundled eight-packet example interleaves an account and a workstation. Repeated observations from the same workstation control provide no independent corroboration. Its later independent observation arrives one second beyond the permitted interval. Five packets are accepted, the duplicate is acknowledged, and the late packet and conflicting ID are rejected. One High transition occurs. [Eight input packets](../fixtures/stream-demo.ndjson) · [Full trace](../docs/data/stream-trace.json)

## State and ordering

| Input condition | Observable behaviour |
|---|---|
| New ID, valid synthetic scope and signal, nondecreasing UTC time in that scope | Emit the current priority, matched rule and supporting event IDs. A priority change carries its previous and new values. The first observation has a null previous value. |
| Entering High | Emit `alert: true` once. A later report on the same subject leaves the escalation open for human review. A conflicting report about the same session updates its cited evidence when it arrives within the correlation window. |
| Same scope, same ID, identical timestamp and signal | Emit `duplicate` even when newer observations have arrived. Leave the existing decision and timestamps intact. |
| An accepted ID is resubmitted with other values | Reject with `conflict`. The original remains authoritative. The same ID may appear independently in a different scope. |
| New ID timestamp earlier than the latest accepted time in its own scope | Reject with `late` and leave the ID available for correction. Other scopes advance independently. Equal timestamps use arrival order. |
| Invalid or unknown fields/signals, malformed JSON, duplicate JSON field names, or lines over 1,024 bytes including newline | Emit a rejection and continue with the next line. Rejected values are omitted from the result. |

Each process holds four fictional case scopes. A scope accepts the 10,000 possible identifiers from E0000 through E9999. It retains each accepted ID and its signature during this process for exact replay detection. The corroboration window retains the latest observation per catalogue signal and the currently latched finding. Expiry uses a 900-second inclusive lookback based on source timestamps. Closing the process clears its state. Starting another process creates a new review session.

The adapter consumes the normalised observation vocabulary in the [API contract](api.md). It demonstrates application-level streaming detection on fictional data. Evaluating a partner deployment requires source-specific adapters, real entity correlation, persistent checkpoints, event-time handling for delayed sources, tenant isolation and replay tests across restarts. A High transition requests verification by a person.

## Fixture validation

Ten labelled scenarios exercise disputed and recognised sessions, the exact timing boundary, missing independent evidence, same-source repetition, independent process observation, recovery, collection gaps and conflicting reports. Four of the ten specify an alert, with source-clock delays of 120, 200, 300 or 900 seconds. The other six specify zero High transitions. The adapter reproduces all ten expected final priorities and alert times. These delays measure elapsed time between supplied observations. Runtime latency and real-world detection accuracy require separate measurements. [Labelled inputs](../fixtures/stream-checks.json) · [Expected and observed results](../docs/data/stream-trace.json)

```sh
python3 scripts/build_stream_trace.py
python3 -m unittest discover -s tests -p test_stream.py -v
```

## Decision time

A separate local microbenchmark passed 40,000 unique (scope, ID) packets into the Python detector. It measured a median of 4.792 µs and a 95th percentile of 6.042 µs per call to `ingest()` on one arm64 host running Python 3.9.6. The input objects were already in memory. These numbers exclude transport, JSON decoding, user-interface updates and model inference. The four subjects and repeated signal patterns provide a CPU timing exercise. Customer workloads would need end-to-end latency measurements, including when their telemetry becomes available. [Machine-readable measurement](stream-benchmark.json)

```sh
python3 scripts/benchmark_stream.py
```
