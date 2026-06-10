# -*- coding: utf-8 -*-
"""
image_gen.py — OPTIONAL AI image generation for slide assets (soft-3D icons, illustrations).

Off by default. Only runs when OPENAI_API_KEY is set; otherwise it tells the caller to
fall back to image_search.py (free Pixabay) or a Sharp-rasterized gradient.

Model: OpenAI Images, **gpt-image-2 preferred** (falls back to gpt-image-1 only if the
account lacks gpt-image-2). Note: gpt-image-2 does NOT support transparent backgrounds —
so for transparent icons we generate OPAQUE (white bg) and key the white out with PIL
(edge flood-fill, preserving interior highlights). gpt-image-1 supports native transparency.

Usage:
  python image_gen.py "isometric soft-3D blue app icon, white background" \
      --filename b-spark.png --aspect 1:1 -o workspace/images          # transparent (default)
  python image_gen.py "blue gradient mesh" --filename bg.png --opaque   # keep background
  python image_gen.py --manifest workspace/images/image_prompts.json -o workspace/images
"""
import argparse
import base64
import io
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ASPECT_SIZE = {"1:1": "1024x1024", "16:9": "1536x1024", "9:16": "1024x1536", "4:3": "1536x1024"}
OPENAI_MODELS = ["gpt-image-2", "gpt-image-1"]  # prefer gpt-image-2; fall back if unavailable


def _load_dotenv() -> None:
    for base in (Path.cwd(), Path.cwd().parent, Path(__file__).resolve().parent):
        f = base / ".env"
        if f.exists():
            for line in f.read_text(encoding="utf-8-sig").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


def _key_white(png_bytes: bytes) -> bytes:
    """Make the white studio background transparent via edge flood-fill (keeps interior whites)."""
    from PIL import Image, ImageDraw
    im = Image.open(io.BytesIO(png_bytes)).convert("RGB")
    KEY = (255, 0, 255)
    w, h = im.size
    for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)):
        ImageDraw.floodfill(im, seed, KEY, thresh=42)
    data = list(im.getdata())
    out = Image.new("RGBA", im.size)
    out.putdata([(0, 0, 0, 0) if px == KEY else (px[0], px[1], px[2], 255) for px in data])
    buf = io.BytesIO()
    out.save(buf, "PNG")
    return buf.getvalue()


def _request(model: str, prompt: str, size: str, transparent: bool):
    key = os.environ["OPENAI_API_KEY"]
    payload = {"model": model, "prompt": prompt, "size": size, "n": 1}
    if transparent:
        payload["background"] = "transparent"
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations", data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        item = json.loads(r.read())["data"][0]
    if item.get("b64_json"):
        return base64.b64decode(item["b64_json"])
    with urllib.request.urlopen(item["url"], timeout=60) as ir:
        return ir.read()


def gen_openai(prompt: str, size: str, want_transparent: bool):
    """Return (png_bytes, is_natively_transparent) or (None, False)."""
    if not os.environ.get("OPENAI_API_KEY"):
        return None, False
    for model in OPENAI_MODELS:
        for transparent in ([True, False] if want_transparent else [False]):
            try:
                raw = _request(model, prompt, size, transparent)
                print(f"  (model: {model}, transparent={transparent})", file=sys.stderr)
                return raw, transparent
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", "replace")
                low = msg.lower()
                if "transparent background is not supported" in low:
                    continue  # same model, retry opaque (then key white)
                if e.code in (400, 404) and "invalid value" in low and "gpt-image" in low:
                    print(f"  {model} unavailable: {msg[:140]}", file=sys.stderr)
                    break  # try next model
                print(f"  {model}: HTTP {e.code} {msg[:160]}", file=sys.stderr)
                return None, False
            except Exception as e:
                print(f"  {model} error: {e}", file=sys.stderr)
                return None, False
    return None, False


def produce(prompt: str, size: str, want_transparent: bool):
    raw, native = gen_openai(prompt, size, want_transparent)
    if raw is None:
        return None
    if want_transparent and not native:
        try:
            raw = _key_white(raw)  # gpt-image-2 opaque → key the white bg
            print("  (keyed white background → transparent)", file=sys.stderr)
        except Exception as e:
            print(f"  white-key failed (keeping opaque): {e}", file=sys.stderr)
    return raw


def main(argv=None) -> int:
    _load_dotenv()
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt", nargs="?")
    ap.add_argument("--filename")
    ap.add_argument("--manifest")
    ap.add_argument("--aspect", choices=list(ASPECT_SIZE), default="1:1")
    ap.add_argument("--opaque", action="store_true", help="keep the generated background (no transparency)")
    ap.add_argument("-o", "--out", default="workspace/images")
    args = ap.parse_args(argv)

    if not os.environ.get("OPENAI_API_KEY"):
        print("OPENAI_API_KEY not set -- AI generation is OFF.\n"
              "Fallback: free stock via image_search.py (Pixabay) -> Sharp gradient -> empty slot.",
              file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    if args.manifest:
        jobs = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    elif args.prompt and args.filename:
        jobs = [{"prompt": args.prompt, "filename": args.filename, "aspect": args.aspect,
                 "opaque": args.opaque}]
    else:
        ap.error("provide PROMPT + --filename, or --manifest")

    rc = 0
    for j in jobs:
        size = ASPECT_SIZE.get(j.get("aspect", args.aspect), ASPECT_SIZE["16:9"])
        want_transparent = not j.get("opaque", args.opaque)
        data = produce(j["prompt"], size, want_transparent)
        if not data:
            print(f"  FAILED (mark Needs-Manual): {j['filename']}", file=sys.stderr)
            rc = 2
            continue
        (out_dir / j["filename"]).write_bytes(data)
        print(f"OK  {out_dir / j['filename']}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
