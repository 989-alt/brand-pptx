# -*- coding: utf-8 -*-
"""
Render every slides/<DIR>/slide-*.html as PNG @ 1280×720, device_scale_factor=2.

Usage:
    python screenshot_slides.py --slides <DIR> --out <DIR>
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slides", required=True, help="directory containing slide-NN.html")
    ap.add_argument("--out", required=True, help="directory to write slide-NN.png")
    args = ap.parse_args()

    src = Path(args.slides).resolve()
    out = Path(args.out).resolve()
    if not src.is_dir():
        print(f"slides dir not found: {src}", file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 720}, device_scale_factor=2
        )
        page = ctx.new_page()
        for s in sorted(src.glob("slide-*.html")):
            page.goto(s.as_uri())
            page.wait_for_load_state("networkidle")
            target = out / f"{s.stem}.png"
            page.screenshot(path=str(target))
            print(f"OK  {target.name}")
        browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
