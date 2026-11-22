"""Open the contract lab against the authenticated loopback API."""
import argparse
import os
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from signalbrief.api import handler_for


def lab_handler(token):
    base = handler_for(token)
    assets = {
        "/": ("integration.html", "text/html; charset=utf-8"),
        "/integration.html": ("integration.html", "text/html; charset=utf-8"),
        "/integration.js": ("integration.js", "text/javascript; charset=utf-8"),
        "/integration.css": ("integration.css", "text/css; charset=utf-8"),
        "/data/contract-examples.json": ("data/contract-examples.json", "application/json"),
        "/mark.svg": ("mark.svg", "image/svg+xml"),
    }

    class IntegrationLab(base):
        def do_GET(self):
            path = urlsplit(self.path).path
            if path == "/lab-mode":
                return self.reply(200, {"mode": "loopback", "schema": 1})
            asset = assets.get(path)
            if asset is None:
                return super().do_GET()
            name, mime = asset
            data = (ROOT / "docs" / name).read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(data)

    return IntegrationLab


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    token = os.environ.get("SIGNALBRIEF_TOKEN", "")
    if len(token) < 32 or not token.isascii() or not token.isalnum():
        parser.error("Set SIGNALBRIEF_TOKEN to a randomly generated alphanumeric secret (32+ characters).")
    with ThreadingHTTPServer(("127.0.0.1", args.port), lab_handler(token)) as server:
        print(f"Open http://127.0.0.1:{server.server_port}/integration.html and enter the same token.", flush=True)
        server.serve_forever()
