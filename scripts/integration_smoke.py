"""Exercise offline fixture mode and the same-origin authenticated UI in Chromium."""
import functools
import json
import secrets
import threading
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright
from serve_integration import ROOT, lab_handler


@contextmanager
def serve(handler):
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}/integration.html"
        finally:
            server.shutdown()
            worker.join()


class Static(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def run():
    with sync_playwright() as player:
        browser = player.chromium.launch()
        try:
            for mobile in (False, True):
                width, height = (390, 844) if mobile else (1440, 900)
                page = browser.new_page(viewport={"width": width, "height": height})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                with serve(functools.partial(Static, directory=ROOT / "docs")) as url:
                    page.goto(url)
                    expect(page.locator("#priority")).to_have_text("High")
                    expect(page.locator("#token")).to_be_hidden()
                    page.select_option("#minutes", "16")
                    page.click("#run")
                    expect(page.locator("#priority")).to_have_text("Review")
                    assert page.locator("#sources li").count() == 1
                    page.select_option("#minutes", "15")
                    page.check("input[value=owner_confirms]")
                    page.click("#run")
                    expect(page.locator("#priority")).to_have_text("Routine")
                    data = json.loads(page.locator("#response").text_content())
                    assert data["frames"][-1]["evidence_ids"] == ["E5001", "E5002"]
                    page.click("#start-stream")
                    expect(page.locator("#stream-state")).to_contain_text("Finished")
                    assert page.locator("#stream-feed li.new-alert").count() == 1
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                token = secrets.token_hex(32)
                with serve(lab_handler(token)) as url:
                    page.goto(url)
                    expect(page.locator("#token")).to_be_visible()
                    page.fill("#token", "invalid")
                    page.click("#run")
                    expect(page.locator("#status")).to_contain_text("401")
                    page.fill("#token", token)
                    with page.expect_response(lambda res: res.url.endswith("/v1/triage")) as got:
                        page.click("#run")
                    assert got.value.status == 200
                    expect(page.locator("#priority")).to_have_text("High")
                    expect(page.locator("#response-title")).to_contain_text("HTTP 200")
                    with page.expect_response(lambda res: res.url.endswith("/v1/demo-stream")) as streamed:
                        page.click("#start-stream")
                    assert streamed.value.status == 200
                    expect(page.locator("#stream-state")).to_contain_text("Finished", timeout=12000)
                    assert page.locator("#stream-feed li.new-alert").count() == 1
                assert not errors, errors
                page.close()
                print(f"Integration lab passed at {width} × {height} (fixture mode and live HTTP).")
        finally:
            browser.close()


if __name__ == "__main__":
    run()
