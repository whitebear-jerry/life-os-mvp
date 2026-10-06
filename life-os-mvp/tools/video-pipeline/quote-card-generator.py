#!/usr/bin/env python3
"""Generate 1080x1350 quote cards from ✨ quote markers in a script."""

from __future__ import annotations

import argparse
import base64
import html
import mimetypes
import re
from pathlib import Path


QUOTE_RE = re.compile(r"^\s*(?:[-*]\s*)?✨\s*(?:\*\*)?[「\"]?(.+?)[」\"]?(?:\*\*)?\s*$", re.MULTILINE)
EXPECTED_QUOTES = [
    "大腦是用來思考的，不是用來記憶的。",
    "別當被瑣事追著跑的倉鼠，當開啟上帝視角的指揮官。",
    "我已經外包記下來了，你可以停止發送警報了。",
]
BEAR_POSTURES = ["fishing", "mountain", "grass"]
DEFAULT_TEMPLATE = """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <style>
    html, body { margin: 0; width: 1080px; height: 1350px; }
    body {
      display: grid;
      place-items: center;
      background: #F4EFE5;
      color: #5D4632;
      font-family: "Songti TC", "STSong", "Noto Serif TC", serif;
      text-align: center;
    }
    .card { width: 820px; }
    .brand {
      display: inline-block;
      padding: 12px 34px;
      margin-bottom: 70px;
      background: #5D4632;
      color: #fffaf1;
      font-size: 34px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .quote { font-size: 66px; line-height: 1.36; font-weight: 700; letter-spacing: 0; }
    .bear { width: 200px; margin: 24px auto; display: block; opacity: 0.95; }
    .footer { color: #5D4632; font-size: 34px; }
  </style>
</head>
<body>
  <main class="card">
    <div class="brand">金句</div>
    <div class="quote">{{QUOTE}}</div>
    <img src="{{BEAR_SRC}}" class="bear" alt="{{BEAR_ALT}}" />
    <div class="footer">《降噪人生》</div>
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
    quotes = []
    for match in QUOTE_RE.finditer(text):
        quote = match.group(1).strip()
        if not quote.endswith(("。", "！", "？", ".", "!", "?")):
            quote = quote + "。"
        quotes.append(quote)
    for quote in EXPECTED_QUOTES:
        if quote not in quotes:
            quotes.append(quote)
    return quotes[:3]


def bear_asset(index: int) -> Path:
    posture = BEAR_POSTURES[(index - 1) % len(BEAR_POSTURES)]
    return Path(__file__).resolve().parents[1] / "slides" / "assets" / f"bear-{posture}.png"


def data_uri(path: Path) -> str:
    mime_type = mimetypes.guess_type(path)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


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
            asset = bear_asset(index)
            html_doc = (
                template.replace("{{QUOTE}}", html.escape(quote))
                .replace("{{BEAR_SRC}}", data_uri(asset) if asset.exists() else "")
                .replace("{{BEAR_ALT}}", f"white bear {BEAR_POSTURES[(index - 1) % len(BEAR_POSTURES)]}")
            )
            page.set_content(html_doc, wait_until="networkidle")
            output = output_dir / f"quote-card-{index:02d}.png"
            page.screenshot(path=str(output), full_page=True)
            print(f"Wrote {output}")
        browser.close()


if __name__ == "__main__":
    main()
