"""Loopback-only reference integration for normalised, synthetic event codes."""
import argparse
import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

from .engine import InvalidInput, triage

MAX_BYTES = 16384


def unique_fields(pairs):
    result = {}
    for field, value in pairs:
        if field in result:
            raise InvalidInput("JSON fields must be unique.")
        result[field] = value
    return result


def parse_body(body):
    def reject_number(_):
        raise InvalidInput("The integration schema uses string values for all scalar fields.")

    try:
        data = json.loads(body.decode("utf-8"), object_pairs_hook=unique_fields,
                          parse_int=reject_number, parse_float=reject_number, parse_constant=reject_number)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        raise InvalidInput("Expected a UTF-8 JSON object.") from None
    if not isinstance(data, dict) or set(data) != {"schema_version", "scope", "events"} or data["schema_version"] != "1":
        raise InvalidInput("Expected schema_version '1', scope and events.")
    return dict(schema_version="1", scope=data["scope"], **triage(data["scope"], data["events"]))


def handler_for(token):
    expected = ("Bearer " + token).encode("ascii")

    class Handler(BaseHTTPRequestHandler):
        server_version = "SignalBrief/1.0"

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *args):
            # Caller-provided paths, credentials and request contents stay out of logs.
            pass

        def reply(self, status, data):
            body = json.dumps(data, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if status == 401:
                self.send_header("WWW-Authenticate", 'Bearer realm="signalbrief"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                return self.reply(200, {"status": "ok", "version": "1.0.0"})
            return self.reply(404, {"error": "Unknown route."})

        def authorised(self):
            auth = self.headers.get_all("Authorization", [])
            return len(auth) == 1 and hmac.compare_digest(auth[0].encode("latin-1"), expected)

        def do_POST(self):
            if self.path != "/v1/triage":
                return self.reply(404, {"error": "Unknown route."})
            if not self.authorised():
                return self.reply(401, {"error": "A valid bearer token is required."})
            if len(self.headers.get_all("Content-Type", [])) != 1 or self.headers.get_content_type() != "application/json":
                return self.reply(415, {"error": "Use application/json."})
            lengths = self.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or self.headers.get("Transfer-Encoding"):
                return self.reply(400, {"error": "Supply exactly one Content-Length and no transfer coding."})
            raw = lengths[0].strip()
            if not raw.isascii() or not raw.isdigit() or len(raw) > 6:
                return self.reply(400, {"error": "Invalid Content-Length."})
            length = int(raw)
            if length > MAX_BYTES:
                return self.reply(413, {"error": "Request exceeds 16 KiB."})
            try:
                body = self.rfile.read(length)
                if len(body) != length:
                    raise InvalidInput("Incomplete request body.")
                data = parse_body(body)
            except InvalidInput as exc:
                return self.reply(400, {"error": str(exc)})
            except TimeoutError:
                return self.reply(408, {"error": "Request timed out."})
            return self.reply(200, data)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    token = os.environ.get("SIGNALBRIEF_TOKEN", "")
    if len(token) < 32 or not token.isascii() or not token.isalnum():
        parser.error("Set SIGNALBRIEF_TOKEN to a random alphanumeric secret of at least 32 characters.")
    with HTTPServer(("127.0.0.1", args.port), handler_for(token)) as server:
        print(f"SignalBrief reference API on http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
