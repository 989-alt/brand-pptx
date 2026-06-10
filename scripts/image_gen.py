# -*- coding: utf-8 -*-
"""
image_gen.py — OPTIONAL AI image generation for slide assets (soft-3D icons, illustrations).

Off by default. Runs only when a provider key is set (chosen at first use — see SKILL.md
"Image generation — ask ONCE at first use"). With no key it tells the caller to fall back
to image_search.py (free Pixabay) or a Sharp-rasterized gradient.

Providers (pick with --provider, or auto-detect by which key is set):
  * openai  — OpenAI Images, key OPENAI_API_KEY. gpt-image-2 preferred (falls back to
              gpt-image-1 if the account lacks it). Cheapest per image.
  * kie     — KIE.AI job API (gpt-image-2-text-to-image), key KIE_API_KEY
              (also accepts KIE_AI_API_KEY / "Kie.ai_API_KEY"). No OpenAI account needed.

Transparency: gpt-image-2 (and KIE, which proxies it) do NOT support transparent
backgrounds — for transparent icons we generate OPAQUE (white bg) and key the white out
with PIL (edge flood-fill, preserving interior highlights). OpenAI gpt-image-1 supports
native transparency.

Usage:
  python image_gen.py "isometric soft-3D blue app icon, white background" \
      --filename b-spark.png --aspect 1:1 -o workspace/images           # transparent (default)
  python image_gen.py "blue gradient mesh" --filename bg.png --opaque    # keep background
  python image_gen.py --provider kie "soft-3D blue cube" --filename c.png # force KIE.AI
  python image_gen.py --manifest workspace/images/image_prompts.json -o workspace/images
"""
import argparse
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ASPECT_SIZE = {"1:1": "1024x1024", "16:9": "1536x1024", "9:16": "1024x1536", "4:3": "1536x1024"}
KIE_ASPECT = {"1:1": "1:1", "16:9": "16:9", "9:16": "9:16", "4:3": "4:3"}
OPENAI_MODELS = ["gpt-image-2", "gpt-image-1"]  # prefer gpt-image-2; fall back if unavailable
KIE_BASE = "https://api.kie.ai"
KIE_KEY_NAMES = ["KIE_API_KEY", "KIE_AI_API_KEY", "Kie.ai_API_KEY", "KIE.AI_API_KEY"]


def _kie_key():
    for name in KIE_KEY_NAMES:
        v = os.environ.get(name)
        if v:
            return v.strip()
    return None


def resolve_provider(requested):
    """Return 'openai' | 'kie' | None based on --provider and which keys are set."""
    if requested in ("openai", "kie"):
        return requested
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if _kie_key():
        return "kie"
    return None


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


def gen_kie(prompt: str, aspect: str):
    """KIE.AI gpt-image-2 (always opaque). Return (png_bytes, False) or (None, False)."""
    key = _kie_key()
    if not key:
        return None, False
    hdr = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body = json.dumps({"model": "gpt-image-2-text-to-image",
                       "input": {"prompt": prompt, "aspect_ratio": KIE_ASPECT.get(aspect, "1:1"),
                                 "resolution": "1K"}}).encode()
    try:
        req = urllib.request.Request(f"{KIE_BASE}/api/v1/jobs/createTask", data=body, headers=hdr)
        with urllib.request.urlopen(req, timeout=60) as r:
            task = json.loads(r.read()).get("data", {}).get("taskId")
        if not task:
            print("  KIE: no taskId returned", file=sys.stderr)
            return None, False
        for _ in range(45):  # poll up to ~3 min
            time.sleep(4)
            q = urllib.request.Request(f"{KIE_BASE}/api/v1/jobs/recordInfo?taskId={task}", headers=hdr)
            with urllib.request.urlopen(q, timeout=30) as r:
                d = json.loads(r.read()).get("data", {})
            st = d.get("state")
            if st == "success":
                urls = json.loads(d.get("resultJson") or "{}").get("resultUrls") or []
                if urls:
                    with urllib.request.urlopen(urls[0], timeout=60) as ir:
                        print("  (provider: kie, model gpt-image-2)", file=sys.stderr)
                        return ir.read(), False
                return None, False
            if st == "fail":
                print(f"  KIE fail: {d.get('failMsg')}", file=sys.stderr)
                return None, False
        print("  KIE: timed out", file=sys.stderr)
    except Exception as e:
        print(f"  KIE error: {e}", file=sys.stderr)
    return None, False


def produce(prompt: str, aspect: str, size: str, want_transparent: bool, provider: str):
    if provider == "kie":
        raw, native = gen_kie(prompt, aspect)
    else:
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
    ap.add_argument("--provider", choices=["openai", "kie"], default=None,
                    help="image provider (default: auto-detect by which key is set)")
    ap.add_argument("--opaque", action="store_true", help="keep the generated background (no transparency)")
    ap.add_argument("-o", "--out", default="workspace/images")
    args = ap.parse_args(argv)

    provider = resolve_provider(args.provider)
    if provider is None:
        print("No image-generation key set -- AI generation is OFF.\n"
              "Set OPENAI_API_KEY (GPT) or KIE_API_KEY (KIE.AI) in workspace/.env, or pick a\n"
              "provider with --provider. Fallback: image_search.py (Pixabay) -> Sharp gradient -> empty slot.",
              file=sys.stderr)
        return 2
    print(f"  provider: {provider}", file=sys.stderr)

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
        aspect = j.get("aspect", args.aspect)
        size = ASPECT_SIZE.get(aspect, ASPECT_SIZE["16:9"])
        want_transparent = not j.get("opaque", args.opaque)
        data = produce(j["prompt"], aspect, size, want_transparent, provider)
        if not data:
            print(f"  FAILED (mark Needs-Manual): {j['filename']}", file=sys.stderr)
            rc = 2
            continue
        (out_dir / j["filename"]).write_bytes(data)
        print(f"OK  {out_dir / j['filename']}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
