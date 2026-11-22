"""Package the workbench and its replay data as one HTML file."""
import argparse
import base64
import json
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "docs"
SITE = "https://rongsenzhang.github.io/signalbrief-lab/"


def package():
    page = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "style.css").read_text(encoding="utf-8")
    app = (WEB / "app.js").read_text(encoding="utf-8")
    data = {
        p.relative_to(WEB).as_posix(): json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((WEB / "data").glob("*.json"))
    }
    # Escape '<' so fixture strings cannot terminate a script element.
    payload = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("<", r"\u003c")
    icon = base64.b64encode((WEB / "mark.svg").read_bytes()).decode("ascii")
    page = page.replace('href="mark.svg"', 'href="data:image/svg+xml;base64,' + icon + '"')
    page = page.replace('src="mark.svg"', 'src="data:image/svg+xml;base64,' + icon + '"')
    page = page.replace('<link rel="stylesheet" href="style.css">', "<style>\n" + css + "\n</style>")
    loader = '<script src="app.js" defer></script>'
    if loader not in page:
        raise ValueError("The workbench loader changed. Update the offline packager.")
    page = page.replace(loader, "<script>window.signalBriefFiles=" + payload + ";</script>")
    page = page.replace('href="./"', 'href="#case"')
    # Optional model download runs from the published HTTPS origin.
    page = page.replace("</body>", '<script>window.signalBriefOnline=' + json.dumps(SITE) +
                        ';</script>\n<script>\n' + app + '\n</script>\n</body>')
    return page


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="destination HTML file")
    args = parser.parse_args()
    args.output.write_text(package(), encoding="utf-8")
