#!/usr/bin/env python3
"""Generate 1080x1080 quote cards from ✨ quote markers in a script."""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path


QUOTE_RE = re.compile(r"✨\s*(?:\*\*)?[「\"]?(.+?)[」\"]?(?:\*\*)?\s*$", re.MULTILINE)
DEFAULT_TEMPLATE = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <style>
    html, body { margin: 0; width: 1080px; height: 1080px; }
    body {
      display: grid;
      place-items: center;
      background: linear-gradient(145deg, #0c1511, #17201a 60%, #2f6b4f);
      color: #f7f7f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .card { width: 820px; }
    .brand { color: #c48935; font-weight: 900; font-size: 34px; margin-bottom: 44px; }
    .quote { font-size: 74px; line-height: 1.24; font-weight: 900; letter-spacing: 0; }
    .footer { margin-top: 48px; color: rgba(247,247,240,.72); font-size: 28px; }
  </style>
</head>
<body>
  <main class="card">
    <div class="brand">白熊人生攻略</div>
    <div class="quote">{{QUOTE}}</div>
    <div class="footer">把人生變成可以升級的作業系統</div>
  </main>
</body>
</html>
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render 3 quote cards from a script.")
    parser.add_argument("--script", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--template", type=Path, default=Path("marketing/quote-card-template.html"))
    return parser


def extract_quotes(script_path: Path) -> list[str]:
    text = script_path.read_text(encoding="utf-8")
    return [match.group(1).strip("。 ") for match in QUOTE_RE.finditer(text)][:3]


def main() -> None:
    args = build_parser().parse_args()
    script_path = args.script.expanduser().resolve()
    if not script_path.exists():
        raise SystemExit(f"Script not found: {script_path}")

    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    template_path = args.template.expanduser().resolve()
    if template_path.exists():
        template = template_path.read_text(encoding="utf-8")
    else:
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text(DEFAULT_TEMPLATE, encoding="utf-8")
        template = DEFAULT_TEMPLATE

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(f"Missing dependency: {exc.name}. Run: pip install -r requirements.txt && playwright install chromium") from exc

    quotes = extract_quotes(script_path)
    if not quotes:
        raise SystemExit("No quote markers found. Add lines beginning with ✨ to the script.")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        for index, quote in enumerate(quotes, start=1):
            html_doc = template.replace("{{QUOTE}}", html.escape(quote))
            page.set_content(html_doc, wait_until="networkidle")
            output = output_dir / f"quote-card-{index:02d}.png"
            page.screenshot(path=str(output), full_page=True)
            print(f"Wrote {output}")
        browser.close()


if __name__ == "__main__":
    main()
