"""Run the optional networked WASM path in Chromium; requires Playwright and internet."""
import argparse
import functools
import http.server
import json
import threading
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "build/browser-smoke.json")
    args = parser.parse_args()
    handler = functools.partial(QuietHandler, directory=str(DOCS))
    sample = json.loads((DOCS / "data/scenarios.json").read_text())["scenarios"][0]
    step = len(sample["events"])
    bad_calls = []
    with http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler) as server, sync_playwright() as driver:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        browser = driver.chromium.launch()
        try:
            context = browser.new_context()
            context.on("request", lambda req: bad_calls.append(req.method)
                       if req.method not in {"GET", "HEAD", "OPTIONS"} else None)
            page = context.new_page()
            issues = []
            page.on("pageerror", lambda error: issues.append(str(error)[:180]))
            page.on("requestfailed", lambda req: issues.append("Request failed: " + str(urlparse(req.url).hostname)))
            base = "http://127.0.0.1:{}".format(server.server_port)
            page.goto("{}/model-lab.html?case={}&step={}".format(base, sample["id"], step))
            page.get_by_role("button", name="Load model and run").click()
            page.wait_for_function(
                """() => /Completed on this device|Inference could not finish/.test(
                         document.getElementById('state').textContent)""", timeout=240_000)
            status = page.locator("#state").inner_text()
            if "Completed on this device" not in status:
                raise RuntimeError("Browser model run failed. " + str(issues[-4:]))
            choice = page.locator("#outcome").inner_text()
            trace = page.locator("#trace").inner_text()
            quote = page.locator("#excerpt").text_content()
            valid = choice == "No model selection" and quote == ""
            if choice.startswith("Model selected "):
                event_id = choice.removeprefix("Model selected ")
                valid = any(e["id"] == event_id and e["text"] == quote for e in sample["events"][:step])
            if not valid or "Reverse answer:" not in trace or bad_calls:
                raise RuntimeError("Source or read-only network check failed")
            report = {"browser": browser.version, "case": sample["id"], "step": step, "status": status,
                      "choice": choice, "trace": trace, "extract": quote}
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report))
        finally:
            browser.close()
            server.shutdown()
            thread.join()


if __name__ == "__main__":
    main()
