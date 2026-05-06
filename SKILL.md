---
name: brand-pptx
description: "Generate brand-consistent, editable PPTX presentations from a design.md token file (awesome-design-md format). Use when the user wants a presentation that mirrors a specific brand system (Linear, Stripe, Apple, etc.) with pixel-perfect alignment. Triggers: 'brand pptx', 'design.md로 ppt', 'awesome-design-md', 'pptx from design system', '브랜드 컨셉 ppt'."
---

# brand-pptx — design.md → editable PPTX (browser-as-truth)

## Why this skill exists

The default pptx skill produces editable PowerPoint, but suffers from three issues observed in production:
1. Text alignment and text-box placement drift (manual coordinates).
2. Decorative elements (badges, dots, circles) misalign with their adjacent text.
3. Designs feel monotonous — same hero/bullet pattern every slide.

This skill solves all three by:
- Taking a **design.md** (awesome-design-md format) as the source of truth — colors, typography, spacing, components are all tokens.
- Authoring slides as **HTML** so the browser's CSS layout engine measures everything (no manual coordinates).
- Converting HTML → PPTX via **html2pptx** so every text/shape becomes editable in PowerPoint.
- Discovering local fonts at runtime and matching them to the brand tone (no Pretendard/Noto Sans KR by default — they read as "AI-generated").

## When to invoke

User asks for a presentation styled after a known brand system or hands you a `design.md` file. Typical inputs:
- A path under `awesome-design-md-main/` (Linear, Apple, Stripe, etc.).
- A custom `design.md` with the standard YAML frontmatter (`colors:`, `typography:`, `spacing:`, `components:`).

If the user only describes a topic without picking a brand, ask **one question** (Socratic, multiple-choice if possible): which brand vibe — minimal/dark (Linear), warm/serif (Apple-style), or technical/grid (Stripe)?

## Inputs

- `design.md` path (required)
- Topic / outline (optional; if absent, propose 6-slide flow Socratically — one question per turn, max 3 questions)

## The workflow

### Phase A — Parse the design system

Run `scripts/parse_design_md.py <design.md>` → emits `tokens.json` (colors, fonts, spacing, radii) + `guardrails.json` (anti-patterns from the Don't section). Auto-detects light/dark mode from canvas luminance.

### Phase B — Discover fonts (no hardcoding)

Run `scripts/font_discovery.py` → scans `C:/Windows/Fonts/` (and `~/AppData/Local/Microsoft/Windows/Fonts/`). Categorizes Korean / Latin / mono families using a curated allowlist. Matches tone keywords from `design.md`'s description against `TONE_KEYWORDS` to score each candidate. Outputs `selected-fonts.json`.

**Never hardcode a font.** Re-run discovery on each invocation — the SKILL must adapt to whatever the user has installed.

**Avoid by default**: Pretendard, Noto Sans KR. They feel AI-generated. Allowed if explicitly requested.

### Phase C — Outline + slide composition

Pick 6 slides by default. Mix component patterns — never repeat the same layout twice in a row unless the content genuinely demands it (table → table is allowed when comparing). Available components:

| Pattern | Use for |
|---|---|
| `hero` | Slide 1: eyebrow + display title + subhead + CTA cluster |
| `data-callout` | A single big number / stat with side context |
| `feature-grid-3up` | Three cards of equal weight (steps, features, principles) |
| `pipeline-diagram` | Linear flow with nodes + arrow + success row |
| `compare-table` | Honest A vs B comparison |
| `cta-banner` | Closing slide: numbered actions + CTA |

Author each slide as an HTML file at `workspace/slides/slide-NN.html`. They all `<link rel="stylesheet" href="base.css">`. The CSS pulls tokens via CSS variables.

### Phase D — Build editable PPTX

Run `scripts/build_pptx.js`:
- Imports `pptxgenjs` + the local `html2pptx` (copied into the workspace so `require()` resolves).
- Sets `pptx.layout = 'LAYOUT_WIDE'` (13.333" × 7.5" → 1280×720px).
- Loops slides, calls `await html2pptx(file, pptx)` per slide.
- Writes `output/<deck>.pptx`.

Each text node becomes a native PowerPoint text box; each `<div>` with a background becomes a native shape. Result is fully editable.

### Phase E — Verify (REQUIRED)

Run `scripts/screenshot_slides.py` to render each HTML at 1280×720@2x → `screenshots/slide-NN.png`. Open every PNG and inspect:
- Eyebrow dot vertically centered with eyebrow text?
- Badges compact (not stretched)?
- Grid columns equal heights?
- Bottom-bar caption + tag on the same baseline?

If any drift appears, **fix the SKILL** (base.css or component template), not the individual slide. Re-render and re-verify.

## Anti-patterns (do NOT)

- **Do not hand-code coordinates** in the build script. Layout lives in CSS only.
- **Do not use python-pptx** for writes — it corrupts shapes (memory rule). Read-only inspection OK.
- **Do not embed slides as a single image** — user explicitly requires editable text/shapes.
- **Do not show page numbers in the top-right** — user explicitly removed.
- **Do not use Pretendard / Noto Sans KR** unless the user asks. Use font_discovery.py.
- **Do not use gradients** if the design.md's Don't section forbids them (check `guardrails.json`).
- **Do not write Korean strings via the Edit tool inside JS source files** — JSX/JS often mangles them. Author Korean directly inside the HTML files (UTF-8) or extract to JSON with `\uXXXX` escapes (global rule).

## Critical CSS contracts (baked into base.css)

These prevent the most common alignment failures:

```css
/* html2pptx requires body to equal slide size */
html, body { width: 1280px; height: 720px; overflow: hidden; }
body { display: flex; flex-direction: column;
       word-break: keep-all; overflow-wrap: break-word; }  /* Korean safety */

.slide { width: 1280px; height: 720px; padding: 64px;
         display: flex; flex-direction: column; position: relative; }

/* badges/buttons must NEVER stretch in a column-flex parent */
.badge, .btn-primary, .btn-secondary { align-self: flex-start;
                                       white-space: nowrap;
                                       min-width: 120px;
                                       width: max-content; }

/* eyebrow row keeps the dot vertically centered with text */
.eyebrow-row { display: inline-flex; align-items: center; gap: 8px;
               white-space: nowrap; }
.eyebrow-row p { white-space: nowrap; }

/* brand-mark caption that must not break mid-word */
.brand-mark, .brand-mark p { white-space: nowrap; }

/* text only inside <p>/<h*> — html2pptx requirement */
```

If a new component needs a non-stretching badge inside a row-flex parent, no extra rule needed (`align-self` is no-op on the cross axis there).

## PowerPoint compatibility hardening (lessons from production)

PowerPoint applies its own font fallback (e.g. Malgun Gothic when SUIT/Pretendard is missing) and re-measures text boxes. This causes the last character of a single-line text to wrap to a new line, or card body text to overflow its container. Three-layer defense baked into this skill:

1. **`scripts/html2pptx.js` — single-line width buffer 10%** (was 2%). Every single-line text box is recorded `max(width × 1.10, width + 24px)` wider than measured, absorbing the metric drift between browser font and PowerPoint fallback font.
2. **`scripts/html2pptx.js` — explicit `wrap` per box.** `wrap: !isSingleLine, autoFit: false`. Multi-line boxes wrap inside the box (so card body text can't overflow); single-line boxes never wrap (so a short button label stays on one line, regardless of fallback metric).
3. **CSS-side hard locks** — `width: max-content; min-width: 120px; white-space: nowrap` on every CTA/badge/brand-mark. For multi-line card body text, give it explicit `width` AND `height` so html2pptx classifies it as multi-line, and prefer soft `<br>` at meaning boundaries over auto-wrap.

If you see "마지막 글자만 다음 줄로 떨어지는 사고" or "카드 본문이 카드 밖으로 흘러나가는 사고" in production PowerPoint, the fix is one of these three layers — usually layer 3 (explicit width/height + meaning-`<br>`).

## File structure

```
brand-pptx/
├── SKILL.md                      ← this file
├── scripts/
│   ├── parse_design_md.py        ← YAML frontmatter → tokens.json + guardrails.json
│   ├── font_discovery.py         ← scan local fonts, tone-match, emit selected-fonts.json
│   ├── build_pptx.js             ← orchestrator: html → editable pptx via html2pptx
│   ├── html2pptx.js              ← copied from skills/pptx so local node_modules resolve
│   └── screenshot_slides.py      ← Playwright render at 1280×720@2x for verification
├── templates/
│   ├── base.css                  ← tokens (CSS variables), text classes, components
│   └── components/
│       ├── hero.html
│       ├── data-callout.html
│       ├── feature-grid-3up.html
│       ├── pipeline-diagram.html
│       ├── compare-table.html
│       └── cta-banner.html
├── references/
│   └── alignment-guardrails.md   ← anti-patterns + why
└── examples/
    └── linear-rag-deck/          ← reference 6-slide deck (Linear DESIGN.md)
```

## Required dependencies

In the workspace (not the skill itself — workspaces own their `node_modules`):
- Node.js: `pptxgenjs`, `playwright`, `sharp`
- Python: `playwright`, `python-pptx` (read-only), `pyyaml`

Install once per workspace:
```
npm i pptxgenjs playwright sharp
pip install playwright python-pptx pyyaml
python -m playwright install chromium
```

## Output

`output/<deck-name>.pptx` — fully editable, brand-consistent, alignment-verified.
