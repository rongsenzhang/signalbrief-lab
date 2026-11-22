# Python integration contract

The static site reads published replay results. The Python service computes the same results for a new sequence of synthetic records on the caller's machine. A provider adapter would map authorised telemetry to the reviewed schema inside the client environment. Each call is stateless and covers one bearer token, one synthetic subject, one ordered sequence and at most 32 events.

For observation-by-observation processing, the [streaming detector](stream.md) accepts interleaved synthetic subjects and emits an alert immediately when independent evidence moves a case into High.

## Start the service

Use Python 3.9 or later. The reference API and topic model use the standard library. Run both lines in the same terminal at the repository root. The randomly generated token stays in the current shell environment. Stop the service with Ctrl+C.

```sh
export SIGNALBRIEF_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
PYTHONPATH=src python3 -m signalbrief.api
```

For an authenticated end-to-end example, run the following block in one shell. The client waits for the background service to start. Both processes inherit the same fresh token.

```sh
export SIGNALBRIEF_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
PYTHONPATH=src python3 -m signalbrief.api --port 8766 &
api_pid=$!
python3 - <<'PY'
import json, os, time
from urllib.error import URLError
from urllib.request import Request, urlopen
for attempt in range(50):
    try:
        with urlopen("http://127.0.0.1:8766/health", timeout=1) as health:
            if json.load(health).get("status") == "ok":
                break
    except URLError:
        time.sleep(0.1)
else:
    raise SystemExit("The demonstration API did not become ready.")
body = {
    "schema_version": "1", "scope": "ACCESS-A",
    "events": [
        {"id":"E5001","time":"2026-11-16T09:00:00Z","signal":"session_opened"},
        {"id":"E5002","time":"2026-11-16T09:05:00Z","signal":"owner_disputes"}
    ]
}
request = Request(
    "http://127.0.0.1:8766/v1/triage", data=json.dumps(body).encode(),
    headers={"Content-Type":"application/json", "Authorization":"Bearer " + os.environ["SIGNALBRIEF_TOKEN"]}
)
with urlopen(request, timeout=5) as response:
    frames = json.load(response)["frames"]
print([(frame["priority"], frame["evidence_ids"]) for frame in frames])
PY
kill "$api_pid"
unset SIGNALBRIEF_TOKEN
```

Expected result is `[('Review', ['E5001']), ('High', ['E5001', 'E5002'])]`. The second event provides independent corroboration within 15 minutes. Either event alone calls for review. Without a valid bearer token the POST returns HTTP 401.

### Try the browser integration lab

The public integration lab provides ten captured request/response examples. To send live authenticated requests, stop any other demo on port 8765, then run the following in a personal terminal.

```sh
export SIGNALBRIEF_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
printf '%s\n' "$SIGNALBRIEF_TOKEN"
python3 scripts/serve_integration.py
```

Open [the local integration lab](http://127.0.0.1:8765/integration.html) and paste the disposable token into that local tab. The server accepts an alphanumeric token of at least 32 characters. Stop it with Ctrl+C and run `unset SIGNALBRIEF_TOKEN` when finished.

| Endpoint | Behaviour |
|---|---|
| `GET /health` | Liveness and version, accessible on loopback without a credential. |
| `POST /v1/triage` | Requires a bearer token and a UTF-8 JSON body. Returns the synthesised events and one decision frame for each event. |
| Other routes | Return HTTP 404 for GET and POST. |

## Accepted input

The top-level fields are `schema_version` (the string `"1"`), `scope` and `events`. Each event has exactly three fields. `id` has the form `E1234` and must be unique within the request. `time` uses UTC ISO timestamps with second precision and a trailing Z. Timestamps must be nondecreasing. `signal` belongs to the scope's allowlist. Field names are case-sensitive.

| Synthetic subject | Signal vocabulary |
|---|---|
| ACCESS-A | access_declined, session_opened, owner_disputes, owner_confirms |
| DEVICE-A | endpoint_block, endpoint_note, process_observed |
| BACKUP-A | backup_late, restore_pending, restore_verified |
| FEED-A | monitor_gap, vague_notice, feed_resumed |

The engine constructs all descriptions from the public signal catalogue. Fields for names, email addresses, addresses, log messages and other free text are rejected. There is no external target, URL input or provider connector. The local service neither persists requests nor writes access logs. The static UI stores its explicit local review choices separately in the browser.

Malformed data, unsupported schemas, duplicate JSON keys and mixed-scope signals return HTTP 400. The service returns HTTP 415 for unsupported content types and HTTP 413 for bodies over 16 KiB. Responses request no caching. The token comparison is constant time. The service binds IPv4 loopback only, with a five-second request socket timeout. The API starts only with an alphanumeric secret of at least 32 characters; use the generation command above.

## Output and integration semantics

`events` contains the approved text and source for each event. A frame contains `event_ids` observed so far, `model.label` and `model.score` for the **latest event**, `priority` for the case, the deciding `rule`, `evidence_ids`, analyst and manager statements, an unknown and a suggested human step. The topic may abstain. The model score is an uncalibrated closed-set topic score. It does not estimate the probability of a threat. The rules never use that number to escalate a case.

The input scope represents one fictional account, workstation, backup service or monitoring feed per call. Cross-record correlations use the same synthetic subject and a 15-minute inclusive lookback. Two records from the same endpoint control cannot supply independent corroboration. A high-priority finding remains latched for human review even when later evidence arrives. The UI records a human disposition separately from those calculated frames. A production adapter would need real entity/session correlation, event deduplication across requests, replay protection, clock-skew handling and approved access to time-synchronised sources.

When the account owner gives conflicting reports after the same recorded session opens, the analyst sees the session and both reports. The case stays at High until a human reconciles the disagreement. Once another session opens, its reports are considered separately.

The demonstration token provides one local access boundary. A shared deployment would require an approved identity provider, tenant authorisation, encrypted transport, credential rotation, operational controls and a documented retention process. No company endpoint, customer record or production authentication configuration was used.

## Reproduce and inspect

```sh
python3 scripts/build_demo.py
python3 -m unittest discover -s tests
python3 scripts/benchmark.py --events 1000000 --output /tmp/signalbrief-evaluation.json
python3 scripts/corpus_check.py --check
```

Read the published [model evaluation and timing record](../docs/data/evaluation.json) and [synthetic source catalogue](../fixtures/signals.json). Timing varies by machine. The routing test and its examples are deterministic.

The optional corpus check downloads a pinned public Loghub OpenSSH sample and verifies its Git blob hash. It sends only log *templates* to the local classifier. There are 27 distinct templates across 2,000 rows. The router assigns a topic to 17 templates, covering 1,062 rows (53.1%). Loghub does not provide the service-team labels this router predicts, so this check measures coverage. Only the aggregate is stored in this repository. An existing byte-identical CSV can be supplied with `--input PATH --check`. [Source snapshot](https://github.com/logpai/loghub/blob/dd61d0952749ee7963bde24220d1be5ede023033/OpenSSH/OpenSSH_2k.log_structured.csv) · [Aggregate result](corpus-check.json)
