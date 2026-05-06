# -*- coding: utf-8 -*-
"""design.md → tokens.json + guardrails.json"""
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("yaml 모듈 필요: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def split_frontmatter(text: str) -> tuple[str, str]:
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        raise ValueError("frontmatter not found")
    return m.group(1), m.group(2)


def extract_do_dont(body: str) -> dict:
    m = re.search(r"##\s+Do'?s and Don'?ts\s*\n(.*?)(?=\n##\s|\Z)", body, re.DOTALL)
    if not m:
        return {"do": [], "dont": []}
    section = m.group(1)

    def pull(label: str) -> list[str]:
        sub = re.search(rf"###\s+{label}\s*\n(.*?)(?=\n###\s|\Z)", section, re.DOTALL)
        if not sub:
            return []
        return [
            re.sub(r"\s+", " ", line.lstrip("- ").strip())
            for line in sub.group(1).strip().splitlines()
            if line.strip().startswith("-")
        ]

    return {"do": pull("Do"), "dont": pull("Don'?t")}


def main(src: Path, out_dir: Path) -> None:
    text = src.read_text(encoding="utf-8")
    fm_raw, body = split_frontmatter(text)
    tokens = yaml.safe_load(fm_raw)
    guardrails = extract_do_dont(body)

    canvas_hex = tokens.get("colors", {}).get("canvas", "#ffffff").lstrip("#")
    r, g, b = (int(canvas_hex[i:i + 2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    tokens["_meta"] = {
        "mode": "dark" if luminance < 0.5 else "light",
        "canvas_luminance": round(luminance, 3),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tokens.json").write_text(
        json.dumps(tokens, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out_dir / "guardrails.json").write_text(
        json.dumps(guardrails, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"OK  brand={tokens.get('name')}  mode={tokens['_meta']['mode']}  "
          f"do={len(guardrails['do'])} dont={len(guardrails['dont'])}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
