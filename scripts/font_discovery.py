# -*- coding: utf-8 -*-
"""
font_discovery.py — 로컬 폰트 스캔 + design.md description 기반 적합 폰트 선택

사용법:
  python font_discovery.py <design.md path> <output dir>

산출물:
  fonts-available.json  : 스캔된 모든 후보 (디버그/투명성용)
  selected-fonts.json   : 디자인 톤에 매칭된 최종 선택
"""
import json
import os
import platform
import re
import sys
from pathlib import Path

# ---------- 1. 블랙리스트 (AI-generic 느낌) ----------
BLACKLIST = {"Pretendard", "Noto Sans KR", "NotoSansKR", "Noto Sans CJK KR",
             "Malgun Gothic", "맑은 고딕"}

# ---------- 2. 알려진 한국어 지원 폰트 카탈로그 ----------
# (filename pattern → font_family, tone, weight_hint)
KOREAN_KNOWN = {
    # 모던 지오메트릭 (tech/craft 톤에 적합)
    r"^GmarketSans(Bold|Medium|Light)\.otf$":  ("Gmarket Sans",   "geometric-modern",  "{w}"),
    r"^SUIT-(Bold|Medium|Regular|Light|Thin)\.otf$":         ("SUIT",            "geometric-modern",  "{w}"),
    r"^IBMPlexSansKR-(Bold|Medium|Regular|Light)\.otf$":     ("IBM Plex Sans KR","geometric-tech",    "{w}"),
    r"^SpoqaHanSansNeo-(Bold|Medium|Regular|Light)\.otf$":   ("Spoqa Han Sans Neo","neutral-business","{w}"),

    # 휴머니스트/콜포레이트
    r"^Hancom Gothic (Bold|Regular)\.ttf$":   ("Hancom Gothic",   "neutral-corporate","{w}"),
    r"^HancomMalangMalang-(Bold|Regular)\.ttf$": ("Hancom Malang", "warm-friendly",   "{w}"),

    # 전통/출판
    r"^HANBatang(B|ExtBB|ExtB|Ext)?\.TTF$":   ("HANBatang",       "elegant-serif",    "{w}"),
    r"^H2(MJ|MJSM|MJRE)\w*\.TTF$":            ("HY 명조",          "elegant-serif",    "regular"),
    r"^H2(GTRM|GTRE|GPRM|GSRB)\w*\.TTF$":     ("HY 고딕",          "neutral-classic",  "{w}"),
    r"^KoPubWorld\s?Dotum.*\.(ttf|otf)$":     ("KoPub World Dotum","quiet-luxury",     "{w}"),
    r"^KoPubWorld\s?Batang.*\.(ttf|otf)$":    ("KoPub World Batang","quiet-publishing","{w}"),

    # 디스플레이 (헤드라인용)
    r"^esamanru OTF (Bold|Light|Medium)\.otf$": ("esamanru",      "playful-modern",   "{w}"),
    r"^NanumSquareRound\w+\.ttf$":            ("NanumSquareRound","rounded-friendly", "regular"),
    r"^Cafe24.*\.(ttf|otf)$":                 ("Cafe24",          "playful-display",  "regular"),
    r"^BlackHanSans.*\.(ttf|otf)$":           ("Black Han Sans",  "heavy-display",    "black"),
    r"^GodoB?\.ttf$":                         ("Godo",            "geometric-display","bold"),

    # 학교/캐주얼
    r"^Hakgyoansim_\w+\.ttf$":                ("학교안심 몬당분필", "casual-school",    "regular"),
    r"^학교안심.*\.ttf$":                       ("학교안심",         "casual-school",    "regular"),
    r"^감탄로드.*\.ttf$":                       ("감탄로드",         "casual-warm",      "regular"),
}

LATIN_KNOWN = {
    r"^Inter[\-]?(Bold|Medium|Regular|Light)?\.(ttf|otf)$":  ("Inter",      "geometric-tech"),
    r"^Poppins-(Bold|Medium|Regular|SemiBold)\.ttf$":         ("Poppins",   "geometric-friendly"),
    r"^OpenSans-(Bold|Regular|SemiBold)\.ttf$":              ("Open Sans",  "humanist-neutral"),
    r"^Cabin.*\.(ttf|otf)$":                                  ("Cabin",      "humanist-neutral"),
    r"^BebasNeue\.otf$":                                      ("Bebas Neue", "condensed-display"),
    r"^RussoOne-Regular\.ttf$":                               ("Russo One",  "geometric-display"),
}

MONO_KNOWN = {
    r"^CascadiaMono\.ttf$":         ("Cascadia Mono",  "tech-mono"),
    r"^CascadiaCode\.ttf$":         ("Cascadia Code",  "tech-mono"),
    r"^consola\w*\.ttf$":           ("Consolas",       "system-mono"),
    r"^JetBrainsMono.*\.(ttf|otf)$": ("JetBrains Mono","tech-mono"),
    r"^GeistMono.*\.(ttf|otf)$":    ("Geist Mono",     "tech-mono"),
    r"^IBMPlexMono.*\.(ttf|otf)$":  ("IBM Plex Mono",  "tech-mono"),
    r"^FiraCode.*\.(ttf|otf)$":     ("Fira Code",      "tech-mono"),
    r"^UbuntuMono.*\.(ttf|otf)$":   ("Ubuntu Mono",    "tech-mono"),
}


# ---------- 3. 톤 매칭 키워드 ----------
TONE_KEYWORDS = {
    "geometric-modern":   ["technical", "craft", "precision", "modern", "tech",
                            "developer", "software", "near-black", "dark"],
    "geometric-tech":     ["technical", "code", "tech", "developer", "engineering",
                            "system", "platform"],
    "neutral-business":   ["business", "corporate", "enterprise", "professional"],
    "elegant-serif":      ["luxury", "luxurious", "elegant", "editorial", "publishing",
                            "premium", "magazine"],
    "quiet-luxury":       ["quiet", "luxurious", "restrained", "minimal", "calm"],
    "playful-modern":     ["playful", "friendly", "fun", "casual", "approachable",
                            "lively", "vivid"],
    "rounded-friendly":   ["friendly", "warm", "approachable", "soft", "round"],
    "warm-friendly":      ["warm", "friendly", "human", "approachable"],
    "heavy-display":      ["bold", "loud", "impact", "punchy", "statement"],
    "geometric-display":  ["display", "headline", "bold", "impact"],
    "casual-school":      ["education", "school", "child", "kid", "playful", "casual"],
    "casual-warm":        ["casual", "warm", "hand-drawn", "human"],
    "humanist-neutral":   ["readable", "neutral", "humanist", "body"],
}


def font_dirs() -> list[Path]:
    p = platform.system().lower()
    home = Path.home()
    if p == "windows":
        return [Path("C:/Windows/Fonts"),
                home / "AppData/Local/Microsoft/Windows/Fonts"]
    if p == "darwin":
        return [Path("/System/Library/Fonts"), Path("/Library/Fonts"),
                home / "Library/Fonts"]
    return [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"),
            home / ".local/share/fonts", home / ".fonts"]


def scan_fonts() -> dict:
    found_kr, found_latin, found_mono = {}, {}, {}
    for d in font_dirs():
        if not d.exists():
            continue
        for f in d.rglob("*"):
            if not f.is_file() or f.suffix.lower() not in {".ttf", ".otf", ".ttc"}:
                continue
            name = f.name
            for pattern, (family, tone, weight_tmpl) in KOREAN_KNOWN.items():
                m = re.match(pattern, name, re.IGNORECASE)
                if m:
                    weight = weight_tmpl
                    if "{w}" in weight_tmpl and m.groups():
                        weight = weight_tmpl.format(w=m.group(1) or "Regular")
                    entry = found_kr.setdefault(family, {"family": family, "tone": tone,
                                                          "weights": [], "files": []})
                    entry["weights"].append(weight)
                    entry["files"].append(str(f))
                    break
            else:
                for pattern, (family, tone) in LATIN_KNOWN.items():
                    if re.match(pattern, name, re.IGNORECASE):
                        entry = found_latin.setdefault(family, {"family": family,
                                                                  "tone": tone, "files": []})
                        entry["files"].append(str(f))
                        break
                else:
                    for pattern, (family, tone) in MONO_KNOWN.items():
                        if re.match(pattern, name, re.IGNORECASE):
                            entry = found_mono.setdefault(family, {"family": family,
                                                                     "tone": tone, "files": []})
                            entry["files"].append(str(f))
                            break

    return {"korean": list(found_kr.values()),
            "latin": list(found_latin.values()),
            "mono": list(found_mono.values()),
            "blacklist": sorted(BLACKLIST)}


def select_for_design(design_md_path: Path, available: dict) -> dict:
    text = design_md_path.read_text(encoding="utf-8").lower()
    description = ""
    m = re.search(r"^description:\s*[\"']?(.+?)[\"']?$", text, re.MULTILINE)
    if m:
        description = m.group(1)
    description += " " + text[:2000]

    def score(tone: str) -> int:
        kws = TONE_KEYWORDS.get(tone, [])
        return sum(1 for kw in kws if kw in description)

    kr = sorted(available["korean"], key=lambda f: score(f["tone"]), reverse=True)
    mono = sorted(available["mono"], key=lambda f: score(f["tone"]), reverse=True)

    selection = {
        "display": kr[0]["family"] if kr else "Arial",
        "body": kr[0]["family"] if kr else "Arial",
        "mono": mono[0]["family"] if mono else "Consolas",
        "rationale": {
            "display_match": {"family": kr[0]["family"], "tone": kr[0]["tone"],
                              "score": score(kr[0]["tone"])} if kr else None,
            "mono_match": {"family": mono[0]["family"], "tone": mono[0]["tone"],
                           "score": score(mono[0]["tone"])} if mono else None,
            "candidates_kr": [{"family": f["family"], "tone": f["tone"], "score": score(f["tone"])}
                              for f in kr[:5]],
        },
    }
    return selection


def main() -> None:
    design_md = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    available = scan_fonts()
    selection = select_for_design(design_md, available)

    (out_dir / "fonts-available.json").write_text(
        json.dumps(available, indent=2, ensure_ascii=False), encoding="utf-8")
    (out_dir / "selected-fonts.json").write_text(
        json.dumps(selection, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"OK  korean={len(available['korean'])} latin={len(available['latin'])} "
          f"mono={len(available['mono'])}")
    print(f"  display = {selection['display']}")
    print(f"  body    = {selection['body']}")
    print(f"  mono    = {selection['mono']}")


if __name__ == "__main__":
    main()
