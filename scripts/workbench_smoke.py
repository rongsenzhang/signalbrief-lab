"""Exercise the recruiter journey against the actual workbench in Chromium."""
import functools
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class StaticFiles(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def check_width(page):
    width = page.evaluate("({content: document.documentElement.scrollWidth, viewport: document.documentElement.clientWidth})")
    assert width["content"] <= width["viewport"], f"Horizontal overflow at {page.url}: {width}"


def check_journey(page, base_url, mobile):
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(base_url)
    expect(page.locator("#case-ref")).to_have_text("SB-101")
    expect(page.locator("#step-count")).to_have_text("Event 1 / 3")
    expect(page.locator("#priority")).to_have_text("Review")
    check_width(page)
    queue = page.locator("#queue")
    assert queue.evaluate("queue => queue.open") == (not mobile)

    page.locator("#next").click()
    expect(page.locator("#ledger li")).to_have_count(2)
    page.locator("#next").click()
    expect(page.locator("#priority")).to_have_text("High")
    expect(page.locator("#ledger li")).to_have_count(3)
    page.locator("#cites").get_by_role("button", name="Show evidence E1013").click()
    expect(page.locator("#event-E1013")).to_be_focused()
    page.locator("#manager").click()
    expect(page.locator("#manager")).to_have_attribute("aria-pressed", "true")
    expect(page.locator("#brief-body")).to_contain_text("without the owner's knowledge")

    page.locator("#draft-review summary").click()
    expect(page.locator("#draft-verdict")).to_have_text("supported with omission")
    expect(page.locator("#draft-text")).not_to_be_empty()
    expect(page.locator("#draft-explanation")).to_contain_text("E1012")
    page.select_option("#review-owner", label="Service desk")
    note = "Use the known contact route and reconcile the disputed sign-in."
    page.locator("#dispositions label").filter(has_text="Escalate").click()
    page.locator("#review-note").fill(note)
    page.locator("#save").click()
    expect(page.locator("#review-count")).to_have_text("1")
    expect(page.locator("#feedback")).to_contain_text("Review saved")
    with page.expect_download() as result:
        page.locator("#export").click()
    download = result.value
    assert download.suggested_filename == "SB-101-event-3-handover.md"
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / download.suggested_filename
        download.save_as(path)
        report = path.read_text(encoding="utf-8")
    for text in ("Priority: High", "E1012, E1013", "Disposition: Escalate", "Review state: Saved", "Next review owner: Service desk", "Confirmed customer impact: Unknown", note):
        assert text in report, f"Missing from downloaded handover: {text}"
    saved_url = page.url
    assert "case=SB-101" in saved_url and "step=3" in saved_url

    if mobile:
        queue.locator("summary").click()
    queue.get_by_role("button").filter(has_text="SB-104").click()
    if mobile:
        assert not queue.evaluate("queue => queue.open")
    expect(page.locator("#case-ref")).to_have_text("SB-104")
    page.locator("#next").click()
    page.locator("#next").click()
    expect(page.locator("#priority")).to_have_text("Routine")
    expect(page.locator("#cites button")).to_have_text(["E1042", "E1043"])
    expect(page.locator("#review-note")).to_have_value("")
    check_width(page)

    page.goto(saved_url)
    expect(page.locator("#case-ref")).to_have_text("SB-101")
    expect(page.locator("#step-count")).to_have_text("Event 3 / 3")
    expect(page.locator("#review-info")).to_contain_text("Escalate")
    expect(page.locator("#review-owner")).to_have_value("Service desk")
    expect(page.locator("#review-note")).to_have_value(note)
    page.locator("#guide-open").click()
    expect(page.get_by_role("dialog", name="Field guide")).to_be_visible()
    expect(page.locator("#guide-routing")).to_contain_text("23 of 24")
    page.locator("#guide-close").click()
    expect(page.locator("#guide")).to_be_hidden()

    page.locator("#nav-model").click()
    expect(page.locator("#case")).to_have_value("SB-101")
    expect(page.locator("#step")).to_have_value("3")
    expect(page.locator("#events li")).to_have_count(3)
    check_width(page)
    page.goto(saved_url)
    page.locator("#nav-api").click()
    expect(page.locator("#priority")).to_have_text("High")
    expect(page.locator("#mode")).to_contain_text("public lab")
    check_width(page)
    assert not errors, errors


def run():
    handler = functools.partial(StaticFiles, directory=ROOT / "docs")
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch()
                try:
                    for width, height in ((1440, 900), (390, 844)):
                        mobile = width == 390
                        context = browser.new_context(
                            viewport={"width": width, "height": height},
                            is_mobile=mobile, has_touch=mobile, accept_downloads=True
                        )
                        try:
                            check_journey(context.new_page(), f"http://127.0.0.1:{server.server_port}/", mobile)
                            print(f"Workbench journey passed at {width} × {height}.", flush=True)
                        finally:
                            context.close()
                finally:
                    browser.close()
        finally:
            server.shutdown()
            thread.join()


if __name__ == "__main__":
    run()
