# brand-pptx

> Claude Code skill that turns a brand `design.md` (awesome-design-md format) into a fully **editable** PowerPoint deck — using the browser as the layout truth.

```
design.md  →  HTML slides  →  html2pptx  →  editable .pptx
```

Every text node lands in PowerPoint as a real text box. Every styled `<div>` becomes a real shape. No raster fallback, no manual coordinates, no Pretendard.

---

## Why this skill exists

The default Claude `pptx` skill produces editable PowerPoint, but in production it shows three failure modes:

1. Text alignment and text-box placement drift because coordinates are hand-coded.
2. Decorative elements (badges, dots, circles) misalign with the text next to them.
3. Decks feel monotonous — every slide is hero + bullet list.

`brand-pptx` solves all three by:

- Treating a **`design.md`** file (colors, typography, spacing, components) as the single source of truth.
- Authoring slides as **HTML** so the browser's CSS engine measures everything.
- Converting HTML → PPTX via a vendored **html2pptx** so every text/shape stays editable.
- Discovering local fonts at runtime and tone-matching them to the brand. Pretendard / Noto Sans KR are excluded by default — they read as "AI-generated."

---

## Install

This is a Claude Code skill. Drop the folder into your skills directory:

```bash
# macOS / Linux
git clone https://github.com/989-alt/brand-pptx ~/.claude/skills/brand-pptx

# Windows (PowerShell)
git clone https://github.com/989-alt/brand-pptx $env:USERPROFILE\.claude\skills\brand-pptx
```

Workspace dependencies (install once per deck workspace, not into the skill folder):

```bash
npm i pptxgenjs playwright sharp
pip install playwright python-pptx pyyaml
python -m playwright install chromium
```

---

## Usage

In Claude Code, invoke with a `design.md` path and an optional topic:

```
/brand-pptx awesome-design-md-main/apple/DESIGN.md
주제: 에이전트 IDE 신규 기능 소개 6슬라이드
```

The skill walks five phases:

| Phase | Output |
|---|---|
| A · Parse | `tokens.json` + `guardrails.json` from the `design.md` frontmatter |
| B · Fonts | `selected-fonts.json` from local font scan + tone match |
| C · Compose | `workspace/slides/slide-NN.html` × N, mixing component patterns |
| D · Build | `output/<deck>.pptx` via `html2pptx` |
| E · Verify | `screenshots/slide-NN.png` at 1280×720@2x for visual QA |

---

## Component patterns

Pick one per slide; never repeat the same pattern twice in a row unless content demands it.

| Pattern | Use for |
|---|---|
| `hero` | Slide 1 — eyebrow + display title + subhead + CTA cluster |
| `data-callout` | A single big number / stat with side context |
| `feature-grid-3up` | Three cards of equal weight (steps, features, principles) |
| `pipeline-diagram` | Linear flow with nodes + arrow + success row |
| `compare-table` | Honest A vs B comparison |
| `cta-banner` | Closing slide — numbered actions + CTA |

Components live as HTML partials in `templates/components/`. Tokens come from CSS variables in `templates/base.css`.

---

## Critical CSS contracts

Baked into `base.css` to prevent the most common alignment bugs:

```css
/* html2pptx requires body to equal slide size */
html, body { width: 1280px; height: 720px; overflow: hidden; }

.slide { width: 1280px; height: 720px; padding: 64px;
         display: flex; flex-direction: column; position: relative; }

/* badges/buttons must NEVER stretch in a column-flex parent */
.badge, .btn-primary, .btn-secondary { align-self: flex-start; }

/* eyebrow row keeps the dot vertically centered with text */
.eyebrow-row { display: inline-flex; align-items: center; gap: 8px; }
```

If you build a new component and the layout drifts in PowerPoint, fix it in `base.css` (or add a new component template) — **never** patch individual slides.

---

## Anti-patterns (do NOT)

- **Don't hand-code coordinates** in `build_pptx.js`. Layout lives in CSS only.
- **Don't use python-pptx for writes** — shape corruption. Read-only inspection is fine.
- **Don't embed slides as a single image** — defeats the entire point.
- **Don't show page numbers** in the top-right.
- **Don't use Pretendard / Noto Sans KR** unless explicitly asked.
- **Don't use gradients** if the `design.md` Don't section forbids them (the parser writes this into `guardrails.json`).
- **Don't author Korean strings via Edit inside JS source** — write Korean directly into the HTML files (UTF-8) or use `\uXXXX` escapes in JSON.

---

## Repo layout

```
brand-pptx/
├── SKILL.md                      ← Claude Code entry point (auto-loaded)
├── scripts/
│   ├── parse_design_md.py        ← YAML frontmatter → tokens.json + guardrails.json
│   ├── font_discovery.py         ← scan local fonts, tone-match, emit selected-fonts.json
│   ├── build_pptx.js             ← orchestrator: html → editable pptx
│   ├── html2pptx.js              ← HTML→PPTX engine (vendored — see Attribution)
│   └── screenshot_slides.py      ← Playwright render at 1280×720@2x for QA
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
│   └── alignment-guardrails.md   ← anti-patterns + reasoning
└── examples/
    └── linear-rag-deck/          ← reference 6-slide deck (Linear DESIGN.md)
```

---

## Attribution

`scripts/html2pptx.js` is a vendored copy of the HTML→PPTX engine that ships with Anthropic's `skills/pptx` skill. It is included so workspace `node_modules` resolves cleanly without having Anthropic's skill installed. All credit for that file goes to Anthropic and the original authors.

The rest of the skill — SKILL.md, base.css, component templates, parse / font / build / screenshot scripts, references, and the example deck — is original work licensed under MIT below.

---

## License

MIT. See [LICENSE](LICENSE).
