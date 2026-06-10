# -*- coding: utf-8 -*-
"""
image_search.py — fetch a free-stock photo/background for a slide (Pixabay-first).

Free for commercial use, no attribution required (Pixabay, Pexels). Downloads the
best match into the workspace so html2pptx embeds it as a native PowerPoint image.

Usage:
  python image_search.py "blue gradient mesh" --filename bg-hero.jpg -o workspace/images
  python image_search.py "laptop on desk" --orientation landscape --min-width 1600

Providers (auto: tries pixabay then pexels if keys present):
  pixabay  → env PIXABAY_API_KEY   (https://pixabay.com/api/docs/  — free key)
  pexels   → env PEXELS_API_KEY    (optional)

No key set → prints how to get a free Pixabay key and exits non-zero (caller falls
back to a Sharp-rasterized gradient or an empty grey slot — see SKILL.md image flow).
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

UA = "brand-pptx/1.0 (+image_search)"


def _load_dotenv() -> None:
    """Load KEY=VALUE from a nearby .env (cwd / parent / script dir) into os.environ.
    Does not overwrite already-set vars; utf-8-sig tolerates a BOM."""
    for base in (Path.cwd(), Path.cwd().parent, Path(__file__).resolve().parent):
        f = base / ".env"
        if f.exists():
            for line in f.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


def _get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def search_pixabay(query: str, orientation: str, min_w: int, min_h: int) -> list[dict]:
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    # pixabay orientation: horizontal | vertical | all
    o = {"landscape": "horizontal", "portrait": "vertical"}.get(orientation, "all")
    qs = urllib.parse.urlencode({
        "key": key, "q": query, "image_type": "photo", "orientation": o,
        "min_width": min_w, "min_height": min_h, "safesearch": "true",
        "order": "popular", "per_page": 24,
    })
    try:
        data = json.loads(_get(f"https://pixabay.com/api/?{qs}"))
    except Exception as e:
        print(f"  pixabay error: {e}", file=sys.stderr)
        return []
    return [{"url": h["largeImageURL"], "w": h["imageWidth"], "h": h["imageHeight"],
             "provider": "pixabay"} for h in data.get("hits", [])]


def search_pexels(query: str, orientation: str, min_w: int, min_h: int) -> list[dict]:
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    o = orientation if orientation in {"landscape", "portrait", "square"} else "landscape"
    qs = urllib.parse.urlencode({"query": query, "orientation": o, "size": "large", "per_page": 24})
    try:
        data = json.loads(_get(f"https://api.pexels.com/v1/search?{qs}", {"Authorization": key}))
    except Exception as e:
        print(f"  pexels error: {e}", file=sys.stderr)
        return []
    out = []
    for p in data.get("photos", []):
        if p["width"] >= min_w and p["height"] >= min_h:
            out.append({"url": p["src"].get("original") or p["src"].get("large2x"),
                        "w": p["width"], "h": p["height"], "provider": "pexels"})
    return out


def main(argv=None) -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("query", help="2-5 keywords")
    ap.add_argument("--filename", required=True, help="output filename, e.g. bg-hero.jpg")
    ap.add_argument("-o", "--out", default="workspace/images", help="output directory")
    ap.add_argument("--provider", choices=["auto", "pixabay", "pexels"], default="auto")
    ap.add_argument("--orientation", choices=["any", "landscape", "portrait", "square"], default="landscape")
    ap.add_argument("--min-width", type=int, default=1200)
    ap.add_argument("--min-height", type=int, default=800)
    args = ap.parse_args(argv)

    providers = {"pixabay": search_pixabay, "pexels": search_pexels}
    order = ["pixabay", "pexels"] if args.provider == "auto" else [args.provider]

    candidates: list[dict] = []
    for name in order:
        candidates += providers[name](args.query, args.orientation, args.min_width, args.min_height)
        if candidates:
            break

    if not candidates:
        if not (os.environ.get("PIXABAY_API_KEY") or os.environ.get("PEXELS_API_KEY")):
            print("No PIXABAY_API_KEY / PEXELS_API_KEY set. Get a free Pixabay key at "
                  "https://pixabay.com/api/docs/ and `export PIXABAY_API_KEY=...`.\n"
                  "Falling back: caller should rasterize a gradient (Sharp) or use an empty slot.",
                  file=sys.stderr)
        else:
            print(f"No results for '{args.query}' at >= {args.min_width}x{args.min_height}.", file=sys.stderr)
        return 2

    candidates.sort(key=lambda c: c["w"] * c["h"], reverse=True)

    from PIL import Image
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / args.filename
    for c in candidates:
        try:
            raw = _get(c["url"])
            im = Image.open(BytesIO(raw))
            if im.width < args.min_width or im.height < args.min_height:
                continue
            im.convert("RGB").save(dest)
            print(f"OK  {dest}  ({im.width}x{im.height}, {c['provider']})")
            return 0
        except Exception as e:
            print(f"  download failed ({c['provider']}): {e}", file=sys.stderr)
            continue
    print("All candidate downloads failed.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
