"""Exercise the HTTP handler in memory, using wire-format request and response bytes."""
import io
import json
import sys
import unittest
import secrets
import threading
from copy import deepcopy
from http.server import HTTPServer
from urllib.request import Request, urlopen
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from build_demo import case_inputs
from signalbrief.api import handler_for


class MemorySocket:
    def __init__(self, wire):
        self.input = io.BytesIO(wire)
        self.response = bytearray()

    def makefile(self, *args):
        return self.input

    def settimeout(self, value):
        pass

    def sendall(self, data):
        self.response.extend(data)


TOKEN = "x" * 32
EXAMPLE = {"schema_version":"1","scope":"ACCESS-A","events":[{"id":"E1011","time":"2026-11-16T09:00:00Z","signal":"access_declined"}]}


def request(body=None, path="/v1/triage", method="POST", token=TOKEN, kind="application/json", length=None):
    payload = body if isinstance(body, bytes) else json.dumps(EXAMPLE if body is None else body).encode()
    headers = [f"{method} {path} HTTP/1.0", f"Content-Type: {kind}",
               f"Content-Length: {len(payload) if length is None else length}"]
    if token is not None:
        headers.append("Authorization: Bearer " + token)
    sock = MemorySocket(("\r\n".join(headers) + "\r\n\r\n").encode() + payload)
    handler_for(TOKEN)(sock, ("127.0.0.1", 1), object())
    head, reply = bytes(sock.response).split(b"\r\n\r\n", 1)
    return int(head.split()[1]), json.loads(reply)


class ApiTests(unittest.TestCase):
    def test_public_health_and_authorised_triage(self):
        self.assertEqual(request(path="/health", method="GET", token=None)[0], 200)
        code, data = request()
        self.assertEqual(code, 200)
        self.assertEqual(data["frames"][0]["model"]["label"], "Identity")

    def test_missing_and_invalid_token(self):
        for value in (None, "invalid"):
            self.assertEqual(request(token=value)[0], 401)

    def test_all_http_replays_match_published_frames(self):
        published = json.loads((ROOT / "docs/data/scenarios.json").read_text())
        by_id = {case["id"]: case for case in published["scenarios"]}
        for case, scope, rows in case_inputs():
            with self.subTest(case=case["id"]):
                status, result = request(body={"schema_version": "1", "scope": scope, "events": rows})
                self.assertEqual(status, 200)
                self.assertEqual(result["frames"], by_id[case["id"]]["frames"])
                self.assertEqual(result["events"], by_id[case["id"]]["events"])

    def test_json_scalars_require_string_fields(self):
        for scalar in (123, 4.5, False, None):
            body = deepcopy(EXAMPLE)
            body["events"][0]["id"] = scalar
            with self.subTest(scalar=scalar):
                self.assertEqual(request(body=body)[0], 400)

    def test_invalid_requests(self):
        for code, arguments in [(404, {"path":"/elsewhere"}), (415, {"kind":"text/plain"}),
                                (400, {"body":b"["}), (413, {"length":17000}),
                                (400, {"length":-1}), (400, {"body":b'{"a":1,"a":2}'}),
                                (400, {"body":dict(EXAMPLE, scope=[])}),
                                (400, {"body":dict(EXAMPLE, private_data="redacted@example.invalid")})]:
            with self.subTest(arguments=arguments):
                status, error = request(**arguments)
                self.assertEqual(status, code)
                self.assertNotIn("example.invalid", json.dumps(error))

    def test_loopback_roundtrip_when_permitted(self):
        token = secrets.token_hex(32)
        try:
            server = HTTPServer(("127.0.0.1", 0), handler_for(token))
        except PermissionError:
            self.skipTest("Sandbox denies loopback listeners; wire-format handler checks still run.")
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/v1/triage"
            post = Request(url, data=json.dumps(EXAMPLE).encode(),
                           headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
            with urlopen(post, timeout=5) as result:
                self.assertEqual(result.status, 200)
                self.assertEqual(json.load(result)["frames"][0]["evidence_ids"], ["E1011"])
        finally:
            server.shutdown()
            server.server_close()
            worker.join()
