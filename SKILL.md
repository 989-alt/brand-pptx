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

## Output convention — always one combined PPTX

A multi-section deck (multi-day workshop, 3차시, multi-chapter manual) is ONE `.pptx`, never split per section. Section transitions are slides *within* the deck (typically dark hero bands at the start of each section). Splitting a multi-section deck into multiple files is a regression — the user has to merge them manually, navigation breaks, and the design system loses its rotational rhythm. If a user asks for "a deck per session," default to one combined file with section dividers and confirm before producing multiple files.

## Planning gate for long-form decks

For decks > 50 slides, do NOT start authoring immediately. Produce a written plan first:
- Total slide count and per-section breakdown (table form)
- Slide-by-slide titles with the assigned component pattern
- Pattern distribution summary (how many `hero-dark`, `pipeline-diagram`, `screenshot-frame`, etc.) — proves the deck won't be monotonous
- Any topic decisions that are user-judgement calls (e.g. "the demo project will be X")

Present the plan, ask 1–3 sharp questions about decisions you cannot make alone (project topic, volume, target audience), then build only after the user has approved or redirected.

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
| `layout-split-color` | 40/60 horizontal split, brand color on one side, content on the other |
| `layout-photo-band` | Full-bleed photo with brand-color band across lower third |
| `layout-color-card-image` | Brand-color card with image floating half-on / half-off |
| `data-callout-diagonal` | Single big number on a diagonal-cut brand-color block |
| `team-photo-circles` | Circular photo grid with brand-color accent dots / badges |
| `quote-overlay` | Photo + dark scrim + large quote text, for north-star slides |
| `infographic-radial-process` | 3~6단계 순환/방사형 프로세스. 중앙 라벨 + 호(arc)/원 단위 + 1:1 텍스트 매칭. (e.g. 반원 5단계, 3-ring venn) |
| `infographic-hierarchy-pyramid` | 3~5단 위계·우선순위·계층. 도형 자체로 비중 시각화. 코너 텍스트로 각 층 설명. 3D variant (`infographic-hierarchy-pyramid-3d`) allowed when "weight" is the message. |
| `infographic-quadrant-diamond` | 4개 카테고리의 균등 분류. 중앙 앵커 + 4분면 (Z-패턴: 좌상→우상→좌하→우하). 매트릭스(2×2)와 구분: 분면 자체가 카테고리이지 좌표가 아님. |
| `infographic-pictogram-bar` | 비교 가능한 정량 데이터 (연도별·항목별 수치). 막대를 데이터 대상 픽토그램으로 치환. 강조 항목만 브랜드 컬러, 나머지는 중성색. |
| `infographic-roadmap-spatial` | 시간·여정 시각화 (timeline, road-shape). 좌→우 진행, 마일스톤마다 아이콘+라벨+분기. |
| `infographic-narrative-stat` | 단일 큰 통계 + 맥락 일러스트. 숫자가 단독 출현하지 않음. HTML/SVG로 그리기 어려운 경우 stock asset 사용 (Adobe MCP `asset_search`, Pixabay, Freepik). |

The first six are the body-density backbone; the next six are layered compositions enforced by the "Composition layers" section; the last six are infographics enforced by the "Infographics" section below. A 100+ slide deck must draw from across all eighteen, not just one group.

Author each slide as an HTML file at `workspace/slides/slide-NN.html`. They all `<link rel="stylesheet" href="base.css">`. The CSS pulls tokens via CSS variables.

### Infographics — use when structure is the message, not as decoration

The reference templates that informed this skill include geometric process diagrams,
pictogram charts, narrative infographics, and 3D pyramids. They work because the
SHAPE itself carries data — not because they add visual interest. Apply the test
below before choosing an infographic pattern over a bullet list or grid.

**Use an infographic when ANY of the following is true:**

1. The data has a **structural relationship** that a list cannot express:
   - Sequential (process steps, timeline, roadmap) → `infographic-radial-process`, `infographic-roadmap-spatial`
   - Hierarchical (priority, foundation→peak) → `infographic-hierarchy-pyramid` (2D or 3D)
   - Categorical with equal weight (4 pillars, 4 quadrants) → `infographic-quadrant-diamond`
   - Comparative numeric (year-over-year, A/B/C/D values) → `infographic-pictogram-bar`
   - Part-to-whole or intersection (overlapping concepts) → 3-ring venn variant of `infographic-radial-process`
2. A single big number needs **immediate emotional context** — pair it with a
   subject-matter illustration so it doesn't read as a bare statistic
   (`infographic-narrative-stat`).
3. The reader will glance at the slide for ≤5 seconds in a live presentation —
   shape-as-data is read faster than a 5-bullet list with the same content.

**Do NOT use an infographic when:**

- The information is genuinely a list of unrelated items (use `feature-grid-3up`)
- The content is a procedure with code/screenshots (use a procedure layout, not
  a radial diagram with abstract icons)
- There are >7 items — infographics break down past 7 nodes; switch to a table
- You're adding it for visual variety only (the test: if you replaced the diagram
  with a bullet list of the same items, would the meaning change? If no, use bullets)

**3D variants — allowed when "weight" is the message.** A 3D pyramid reads as
"the bottom carries the top." A 3D bar reads as "this volume is bigger than that."
Use 3D ONLY when the visual weight of the shape is itself the argument. Flat
information (lists, equal-weight comparison, sequences) with 3D applied is
decoration — that fails the test. If HTML/SVG implementation is impractical
(complex isometric scenes, photorealistic 3D), use stock assets via Adobe MCP
`asset_search`, Pixabay, or Freepik — link as `<img src="../images/<name>">` so
html2pptx places them as native PowerPoint images.

**Deck-wide distribution target:**

- 20–30% slides use an infographic pattern (`infographic-*`)
- 50–60% slides use body-density patterns (`feature-grid`, `compare-table`, `hero`, etc.)
- 10–20% slides are layered composition slides (`layout-*`, `quote-overlay`)
- Never two consecutive infographic slides of the same pattern. A radial-process
  slide followed by another radial-process slide reads as "the AI ran out of
  ideas." Mix: radial → narrative-stat → pyramid → (body slide) → pictogram-bar.

### Authoring-time guardrails — apply BEFORE writing each slide, not after

The audit in "Iterate in 5-slide batches" exists to catch failures, but failures are cheaper to *prevent* than to *fix*. Before writing each slide's HTML — not after rendering — walk this checklist. The rules below are scattered across "Voice and copy rules" / "Slide-level composition discipline" / "Composition layers"; this is the consolidated per-slide gate that applies them at authoring time.

**Universal (every slide):**
- Surface mode picked from the rotation rhythm (not default canvas)
- Composition pattern differs from the previous slide
- The slide is *layered*, not flat canvas + black-on-white text + hairlines
- One key phrase identified, styled with the hierarchy (color · weight · size)
- Title is declarative — no `왜 ~인가` / `어떻게 ~할까` / `Why X?` self-questioning forms
- No filler phrases (`함께 알아볼까요?`, `Let's dive in`), no emoji, no per-slide page numbers

**If COVER or SECTION DIVIDER:**
- Three textual elements maximum: one identifier (eyebrow OR brand-mark, never both) + one headline + one supporting line
- No "next session preview" labels (`2차시 → ...`)
- No duplicate identifiers (`SESSION 01 / 03` text + `1차시` badge both saying the same thing)
- No per-slide operational metadata (`약 3시간 · 슬라이드 32장`)

**If BODY SLIDE with a split layout (`split-2`, `layout-two-tone`, `layout-color-card-image`, `layout-split-color`):**
- Two columns approximately balance in mass — neither side is half-empty
- If a decorative card stretches next to a text list (checklist, steps): the card has `.card-row-aligned` (margin-top: 4px) AND the list's `:last-child` has `padding-bottom: 0` so edges meet text bounds
- Paired columns use **identical top and bottom padding** values in base.css (`.lhs` and `.rhs` do not drift to 80/64)
- No `margin-top: auto` next to fixed-gap siblings — that *guarantees* one outlier gap. Use `justify-content: space-between` on the column instead (groups must be comparable in size), or compute a fixed gap that fills the column
- Footer-row, if present, carries NEW information (key principle, sharp contrast, forward pointer) — never a recap of what the body cards already show

**If a CARD on any slide:**
- Focal block (big number, big quote, callout headline) and its supporting copy read as one block — no `margin-top: auto` orphaning a single aux line at the bottom while the middle goes blank
- Card content density matches the surrounding rhythm (gaps between sub-elements harmonize with column-level gaps)
- If the card stretches to match a sibling's height and the natural content is short, fill the middle with a meaningful unit (secondary stat, divider + caption, supporting bullets) — never leave the middle empty

**If body text sits in a card OR a column narrower than ~400px (any layout):**
- **Hard-break the body text with `<br>` at meaning boundaries.** Do NOT rely on auto-wrap. The browser renders with the linked `@font-face` (e.g. Gmarket Sans) and may show 2 lines fitting comfortably; PowerPoint then falls back to Malgun Gothic / a wider Korean default and the same text overflows the card horizontally. Hard breaks survive font fallback because each line's content is fixed at authoring time, not re-measured at render time.
- Break at **clauses or adverbial phrases** that read naturally on their own line (`코드를 직접 쓰지 않고,` / `AI에게 의도를 전달해` / `코드를 만들게 하는 방식.`). Avoid orphan modifiers hanging alone (`데이터·저작권` alone on a line as a dangling object).
- **Match line counts across sibling cards.** If three cards sit side-by-side, all three bodies should be 3 lines (or all 2 lines). Mismatched counts (3/3/2) destroy the grid rhythm. Rewrite the odd-one-out's prose to match — that is the design constraint, not an option.
- Each line ≤ ~12 Korean characters at 14px body in a 280–320px-inner card. Fallback-font width inflation is ~10–15%; the 12-char line still fits with margin to spare.
- This rule does NOT apply to body text in wide columns (>400px) — auto-wrap is safe there because the column has enough horizontal slack to absorb fallback-font width drift.

**If a CHECKLIST or numbered STEP list:**
- `:last-child` has `padding-bottom: 0` and `border-bottom: none` if paired with a stretched card next to it

**If INFOGRAPHIC slide (any `infographic-*` pattern):**
- One visual unit (arc, segment, pictogram bar, quadrant, tier) maps to exactly one text unit (label + 1~2 line description). No "this arc covers items A, B, C."
- The visual unit must carry MEANING — pictogram bars should be the subject of the data (factories for factory counts, books for reading volume, code icons for coding). Abstract shapes (plain circles, squares) acceptable only when no meaningful pictogram exists.
- Color follows the design system's primary + at most one accent or a single hue ramp (e.g. lavender 5-step shade ladder for hierarchy). Banned: rainbow palettes (red/orange/yellow/green/blue all together) unless the brand explicitly allows multi-hue.
- Numbered sequences (01·02·03) must visually progress — clockwise rotation, left-to-right, or Z-pattern (좌상→우상→좌하→우하). Random placement breaks the read order. **For quadrant-diamond specifically, use Z-pattern and verify the diamond's internal STEP labels and the side cards' STEP labels are at matching Y positions.**
- Central anchor (if used) carries the slide's noun phrase ("5 STAGE DESIGN CYCLE", "4 PILLARS") — never a verb ("알아봅시다") or filler.
- Icons inside the diagram use a SINGLE icon family (all outlined, OR all filled — never mixed). Build inline SVGs or import from Lucide/Heroicons/Phosphor; don't import random emoji-style icons.
- The infographic occupies 55–70% of slide area; remaining space is for the title, eyebrow, and footer (if any). An infographic crammed into 30% with body text dominating defeats the purpose — switch to a body layout instead.
- For `infographic-narrative-stat`: the big number MUST be accompanied by a subject-matter illustration. Stock asset via Adobe MCP / Pixabay / Freepik is allowed when inline SVG is impractical — drop the file under `workspace/images/` and link with `<img>` (html2pptx embeds it as a native PowerPoint image).
- For `infographic-pictogram-bar`: all columns share an identical callout/header format. Don't mix plain-text headers on lighter columns with a callout box on the accent column — that reads inconsistent. Accent column = same shape, brand-color fill.
- For `infographic-hierarchy-pyramid-3d`: SVG cuboid stacking (front rect + top parallelogram + right parallelogram per tier) survives html2pptx as native shapes. CSS 3D transforms (`transform: rotateX`) do NOT — they flatten on export. Always author 3D as SVG polygons, never CSS transforms.
- For `infographic-roadmap-spatial`: nodes that stagger vertically (Q1 above curve, Q2 below) must verify the lowest node + its description fits inside the 720px canvas. Curve amplitude limited to ~80px above/below midline to leave room for two-row descriptions.

**Edge and spacing audit (do this in your head before declaring the HTML done):**
- Identify the implied horizontal lines (where shapes meet text columns). Both the *top* and *bottom* of each shape must align with the first/last text edges of the adjacent column to within 8px
- No single gap on the slide is more than 2× the next-largest gap

**If any item above cannot be ticked, restructure the slide BEFORE writing HTML.** Do not draft "and we'll fix it during audit." Audit is the safety net, not the design phase.

### Composition layers — never one flat plane

A slide that is one solid background + black-on-white text with a thin hairline reads as a wireframe, not a finished slide. The reference templates that informed this skill (AQUA aquatic, EcoSport sport-report, navy/cream business, Prezfull architectural) deliberately layer surfaces, photos, and brand-color blocks so the eye lands on a focal point. Replicate that — every slide must compose, not just place.

**Layer treatments — use at least one per slide; two when the content allows.**

| Composition | When to use |
|---|---|
| `layout-split-color` | Section openers, big quotes, north-star statements. 40/60 split with the brand color on one side, content on the other. |
| `layout-photo-band` | Section dividers, hero, key claim. Full-bleed photo with a brand-color band crossing the lower third where the title sits. |
| `layout-color-card-image` | Feature highlights, leader / team profile. Brand-color rectangle, image floats half-on / half-off the card. |
| `data-callout-diagonal` | Single big number on a diagonal-cut brand-color block (parallelogram clipped from a corner; not symmetric). |
| `team-photo-circles` | Team grid, gallery. Photos clipped to circles, paired with a small brand-color dot or numeric badge. |
| `quote-overlay` | North-star statement. Photo + dark scrim + large quote text, brand-color rule above the attribution. |
| `layout-two-tone` | Body slides that would otherwise be all white. Split the canvas into two adjacent surface tokens (e.g. cream + navy, warm-white + brand). |
| `text-anchor-block` | Display headings on otherwise plain canvases. Semi-transparent brand-color rectangle anchors the title from behind. |

Distribution targets (deck-wide, not per-slide rule):

- ≥ 40% slides with a photo, image inset, or screenshot as a primary visual element
- ≥ 30% slides with a brand-color block ≥ 25% of canvas area (not just an eyebrow stripe or a thin top-bar)
- ≤ 30% slides on a 100% canvas color with no photos and no color blocks beyond an eyebrow — these are body-density slides where the text *is* the visual
- 0% slides where the only visual elements are three or more thin hairlines and black-on-white text — that is a wireframe, not a finished slide
- 0% slides on a 100% solid brand-color canvas with white text and no image / shape / contrast layer — that reads as an ad banner, not a slide

**Surface rotation rhythm.** Read `design.md`'s surface tokens (e.g. `surface-dark`, `surface-soft`, `surface-card`, `surface-brand`) and rotate them deliberately:

- 50–60% slides on light canvas (body, procedure, comparison, grids) — but composed, not flat
- 15–25% slides on the dark surface (section covers, key statements, closer slides, important data callouts)
- 10–20% slides on a soft / cream / off-white surface (textural variety, recap, footer-style summary)
- 10–15% slides where the brand color is the primary background (north-star slides, big quote, single-number data callouts)

Place dark and brand-color slides at section boundaries AND at content peaks where a single sentence carries the chapter's argument — the same way the brand site uses a hero band to anchor a page. Two consecutive same-surface slides are allowed only at a section transition (closer of section N + opener of section N+1). Three same-surface slides in a row is a regression.

If `guardrails.json` has a "Don't repeat the same surface mode across two consecutive bands" entry (BMW does), enforce it.

### Transparency and opacity — composition tools, not ornament

The reference templates use opacity to create depth without ornament:

- **Photo overlays.** Brand color at `rgba(R, G, B, 0.78–0.92)` on top of a photo so the photo stays legible while the slide still reads as the brand. Banned: a 100% opaque brand-color tile *next to* a photo with no overlap — that's a flat split, not a layered composition.
- **Behind-text scrims.** When text sits over a photo, add a gradient scrim on the photo's lower third (`linear-gradient(transparent → rgba(0,0,0, 0.55))`) so contrast is AA without darkening the whole image. Never let large text float over an unscrimmed photo.
- **Card veils on tinted canvases.** `rgba(255,255,255, 0.88–0.92)` cards on a brand-tinted or cream canvas read more sophisticated than `#ffffff` solid cards on the same canvas.
- **Quiet branded dividers.** `rgba(brand, 0.12)` instead of the neutral `--c-hairline` when a divider should feel branded but quiet.

Add these tokens in `base.css` (RGB pulled from `tokens.json`, never hardcoded):

```css
:root {
  --c-primary-rgb: 28, 105, 212;        /* emit alongside --c-primary in parse_design_md.py */
  --alpha-scrim-bottom: rgba(0,0,0, 0.55);
  --alpha-brand-soft:   rgba(var(--c-primary-rgb), 0.12);
  --alpha-brand-veil:   rgba(var(--c-primary-rgb), 0.85);
  --alpha-card-veil:    rgba(255,255,255, 0.90);
  --alpha-dark-veil:    rgba(0,0,0, 0.30);
}
```

`parse_design_md.py` must emit `--c-primary-rgb` (and any other channel-needed tokens) so `rgba()` references work without hardcoding. `tokens.json` carries the same values for downstream scripts.

### Photos and imagery — first-class content layer

Empty grey screenshot slots remain correct for procedure / "the user pastes their own screenshot" slides. But section openers, north-star slides, and gallery slides should use real reference imagery:

- Reference photos live in `workspace/images/` and link via `<img src="../images/<name>.jpg">` so html2pptx places them as native PowerPoint images (editable, replaceable in the file).
- Subject-matter photos must carry meaning — a laptop screen, an architectural detail, a person in the actual context being described. Generic stock (smiling professional pointing at a laptop, abstract "innovation" gradient art, neural-network glow) is banned. It cheapens the deck.
- Photos must respect the palette. If `design.md` is monochrome blue, prefer photos that already lean blue, or convert to grayscale in the source file before linking. The composition layer above the photo (brand band, scrim, color overlay) is what makes the slide feel branded — not a tinted photo.

If the topic genuinely has no photo material (a pure coding tutorial), substitute heavier color-block compositions and geometric accents — never default to "every slide is white canvas with black text."

### Phase D — Build editable PPTX

Run `scripts/build_pptx.js`:
- Imports `pptxgenjs` + the local `html2pptx` (copied into the workspace so `require()` resolves).
- Sets `pptx.layout = 'LAYOUT_WIDE'` (13.333" × 7.5" → 1280×720px).
- Loops slides, calls `await html2pptx(file, pptx)` per slide.
- Writes `output/<deck>.pptx`.

Each text node becomes a native PowerPoint text box; each `<div>` with a background becomes a native shape. Result is fully editable.

### Phase E — Verify (REQUIRED)

Verification is **two-stage**. Browser screenshots verify the SKILL's CSS layout. PPTX/PDF rendering verifies how PowerPoint actually shows the deck — and that is the deliverable, not the screenshot.

**Stage 1 — browser screenshots.** Run `scripts/screenshot_slides.py` to render each HTML at 1280×720@2x → `screenshots/slide-NN.png`. Open every PNG and inspect:
- Eyebrow dot vertically centered with eyebrow text?
- Badges compact (not stretched)?
- Grid columns equal heights?
- Bottom-bar caption + tag on the same baseline?

**Stage 2 — PPTX/PDF rendering (REQUIRED, do NOT skip).** After `build_pptx.js` produces the `.pptx`, render its actual PowerPoint output to PNG:

```python
# pdf2png.py — fast PDF→PNG for verification
import sys, fitz
from pathlib import Path
pdf, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
for i, page in enumerate(fitz.open(pdf), 1):
    page.get_pixmap(dpi=144).save(out / f"pdf-{i:03d}.png")
```

Open the `.pptx` in PowerPoint → File → Export → PDF (or use LibreOffice headless: `soffice --headless --convert-to pdf <file>.pptx`). Then run `python pdf2png.py output/<deck>.pdf pdf-renders/`. Compare each `pdf-NNN.png` against the matching `slide-NN.png` from Stage 1.

**What only Stage 2 catches:**
- **Font-fallback overflow.** Browser uses linked `@font-face` (Gmarket Sans, etc.); PowerPoint falls back to a wider Korean default (Malgun Gothic) when the original isn't installed in the client's PowerPoint font path. Body text that wrapped to 2 clean lines in browser overflows the card horizontally in PowerPoint. Stage 1 cannot see this. Stage 2 always does.
- **Single-line tail-wrap.** A button label or eyebrow that fits on one line in browser may have its last character drop to a second line in PowerPoint (the 10% width buffer in `html2pptx.js` absorbs most cases, but not all).
- **Glyph-metric drift on display type.** Display headlines may render at noticeably different proportions in PowerPoint vs browser. Layout boxes are still at the right Y, but the text inside reads tighter or looser.
- **Silently-dropped section/body backgrounds.** If a slide authors `body { background-image: url(...) }` or `<section style="background-image:url(...)">`, html2pptx does NOT translate that to a slide background. Stage 1 PNG looks correct (browser renders the bg-image fine). Stage 2 reveals that the slide background fell back to the canvas color and the text on it (often `var(--c-on-dark)` ≈ near-white) is invisible. **Always inspect Stage 2 for any slide that was supposed to be dark / branded / full-bleed.** If the symptom appears, fix per layer 5–6 in the hardening section.

**Stage 2 is non-negotiable for decks > 20 slides.** Browser PNG verification alone is insufficient because the most catastrophic failure mode (silently-dropped backgrounds, layer 5) shows ZERO drift in Stage 1 and renders entire slides illegible in Stage 2. Decks under 20 slides may skip Stage 2 only if every slide uses `.slide.canvas` or `.slide.dark` class-based backgrounds (no inline `background-image`).

**Diagnostic when Stage 1 ≠ Stage 2.** If a slide looks fine in screenshot but wrong in PDF:
1. Check whether the difference is **layout** (boxes at wrong Y) or **content** (font-fallback rendering inside correctly-positioned boxes). Most "drift" is the latter and only the offending text needs `<br>` reflow.
2. Confirm with `debug-positions.js` — a small Playwright script that walks key elements and prints `getBoundingClientRect()`. If the browser positions match expected layout, html2pptx is faithful and the issue is PowerPoint's rendering. If positions are wrong in browser, the CSS itself needs fixing.

```js
// debug-positions.js — print measured positions for one slide
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const slide = path.resolve(process.argv[2]);
  const browser = await chromium.launch();
  const page = await (await browser.newContext({ viewport: { width: 1280, height: 720 } })).newPage();
  await page.goto('file://' + slide.replace(/\\/g, '/'));
  await page.waitForLoadState('networkidle');
  console.log(JSON.stringify(await page.evaluate((sels) => sels.map(s => [...document.querySelectorAll(s)].map(el => {
    const r = el.getBoundingClientRect();
    return { sel: s, cls: el.className, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
  })), process.argv.slice(3).length ? process.argv.slice(3) : ['.split-lhs > *', '.split-rhs > *']), null, 2));
  await browser.close();
})();
```

If any drift appears at either stage, **fix the SKILL** (base.css or component template, or insert `<br>` at meaning boundaries in the slide HTML), not by hand-tweaking coordinates. Re-render and re-verify both stages.

### Iterate in 5-slide batches — never write all slides at once

For decks > ~10 slides, do NOT generate the entire deck in one pass. Author 5 slides → render screenshots → open and inspect every PNG → fix any issues in `base.css` or the slide HTML → only then continue to the next batch of 5. The benefits compound:

- A layout bug caught at slide 5 doesn't propagate into slides 6–123.
- The user sees progress and can redirect tone/voice early, not after the entire deck is wrong.
- Each batch is a self-contained checkpoint. If the user pauses or context is compressed, you can resume from the last verified batch without re-checking earlier slides.

The batch audit below is the SAFETY NET, not the design phase. The discipline must already be applied at authoring time via "Authoring-time guardrails" in Phase C. The audit catches what slipped through; if it catches the same class of failure twice, the authoring guardrail itself needs sharpening.

Within each batch, before moving on, confirm:
1. Korean text renders (no `□` tofu, no Latin fallback metric drift).
2. Surface rotation looks intentional, not random — check the previous batch's last slide → this batch's first slide transition.
3. No two consecutive slides use the same component pattern unless the content demands it.
4. Screenshot slots, if any, are empty grey rectangles with no helper text inside.
5. Check to ensure that the text does not overlap with other text or elements, or extend beyond the layout. If it overlaps or extends beyond the layout, wrap the text based on the context.
6. Each slide must have a key phrase. Emphasize important phrases, ordinary phrases, and unimportant phrases in that order by varying the color, boldness, and font size.
7. Run the pre-ship audit from "Slide-level composition discipline": covers/dividers ≤ 3 textual elements, footer-rows say something new, split-layout columns approximately balance, no `margin-top: auto` orphaning card aux text, every visible element earns its place.
8. Edge-alignment audit — shapes and adjacent text columns share their first/last horizontal lines. Paired columns' bottom (and top) anchors coincide on the same Y. No element floats with edges 8px+ off the implied composition lines.
9. Spacing-rhythm audit — no single gap on a slide exceeds 2× the next-largest gap. No `margin-top: auto` next to fixed-gap siblings. Inset compensation applied where decorative cards meet text columns.
10. PPTX/PDF render audit — build the `.pptx`, export to PDF, render `pdf-NNN.png`, compare to `slide-NN.png`. Look specifically for: card body text overflowing the card's right edge (font-fallback width inflation); single-line button/eyebrow text dropping its last character to a second line; sibling cards having mismatched body line counts after fallback re-flow. Browser screenshots alone are insufficient — the deliverable is the PPTX, and the PPTX renders with PowerPoint's font fallback, not the browser's `@font-face`.

Do not "catch up later" — every slide ships only after its batch passed inspection at BOTH stages. If a batch needs a base.css fix or `<br>` reflow, re-render the *entire deck so far* (including earlier batches that share the same CSS), not just the current 5 — the fix may regress them.

## Voice and copy rules (apply to every slide)

These prevent the deck from reading "AI-generated." They are universal — apply them regardless of the brand or topic.

- **No self-questioning titles.** Banned title forms: `왜 ~인가`, `어떻게 ~할까`, `무엇이 ~인가`, `Why X?`, `How does X work?`. Replace with declarative statements or noun phrases. Examples:
  - `왜 토큰을 알아야 하나` → `토큰을 이해해야 하는 이유` or `토큰이 비용·한계와 직결되는 지점`
  - `Why caching matters` → `Caching reduces cost and latency` or `The caching dividend`
- **No slide numbers** anywhere on the slide (no `01 / 24` corner, no `Page 3` footer). Section dividers and the deck table of contents do the navigation work.
- **No filler text.** Banned phrases: "함께 알아볼까요?", "이번 시간에는 ~을 배워봅시다", "Let's dive in", "Welcome!", "any questions?", and the "이제 ~을 살펴보겠습니다" transition lead-in.
- **No emoji** unless the user explicitly requests them. This includes section markers, bullet replacements, and decorative checkmarks.
- **No empty placeholder copy in screenshot slots.** A screenshot frame is a clean grey rectangle (use the design.md's `surface-card` or `surface-soft` token for fill). Do NOT write "여기에 스크린샷을 넣으세요", "Insert screenshot here", "[SCREENSHOT]", or arrows pointing into the box. The slide's title and body copy must explain what the user should capture; the slot itself stays empty so it remains presentable in print and live demos.
- **Imperative procedure copy.** Step-by-step slides start each step with a verb ("터미널을 연다", "Open the terminal"), not a question or a noun fragment.
- **Acronyms expanded once.** Full form on first appearance, abbreviated thereafter.

## Slide-level composition discipline (every element earns its place)

These rules complement "Composition layers" (which governs deck-wide rotation) by governing what happens *inside* a single slide. They were extracted from production failures observed when slides were rendered: metadata overload on covers, footer-rows that recap the body, split layouts with one column half-empty, and cards with auxiliary text orphaned at the bottom.

### Cover and section-divider economy

A cover slide and a section divider have ONE job: slow the eye on a single phrase. They are NOT metadata sheets. Limit them to **three textual elements maximum**:

- One identifier — either a `brand-mark` (logo + caption) OR an `eyebrow-row`, never both
- One display headline (the moment the slide exists for)
- ONE supporting line — either a single-sentence subhead OR a single bottom caption (`약 3시간 · 32장` style) — never both, never two captions in opposite corners

What this rules out:

- top `brand-mark` + `eyebrow-row` + headline + subhead + bottom-left caption + bottom-right caption + top-right badge — six elements competing for attention; the headline loses voltage
- "next session preview" labels on a section divider (`2차시 → ANTIGRAVITY로 첫 웹앱` on a 1차시 divider) — dividers pause the deck, they do not preview
- duplicate identifiers (e.g. `SESSION 01 / 03` text on the left AND a `1차시` coral badge on the right meaning the same thing)
- per-slide operational metadata (`약 3시간 · 슬라이드 32장`, `Updated 2026-05`, internal session counts) — that belongs in the deck's table-of-contents slide, not on every divider

A cover or divider that feels "too empty" with three elements is doing its job correctly. The drama lives in the typography, not in the metadata density.

### Footer-rows carry new information, not recap

A `footer-row` at the bottom of a body slide should carry a NEW claim, contrast, or forward-pointing pointer — never a restatement of what the cards / pipeline / list above have already shown.

| The body shows | Do NOT write in the footer |
|---|---|
| Cards labelled `1차시 / 2차시 / 3차시` | `총 3차시 · 약 9시간` |
| Pipeline with 4 nodes | `4단계 절차` |
| Checklist of 5 items | `5가지 준비물` |
| Compare table A vs B | `A와 B 비교` |

If the footer-row has nothing new to say, **delete the entire row** — including its hairline divider. An empty hairline above redundant text reads as visual noise twice.

What a footer-row CAN say: a key principle that reframes the body (`완성도 ≠ 시간 투자량 — 의도 명확성이 90%`), a sharp contrast (`AI는 만든다. 사람은 판단한다.`), or a forward pointer to a non-obvious next slide. If you cannot write that line in one breath, the footer should not exist.

### Column balance in split layouts

In any 2-column layout (`split-2`, `layout-two-tone`, `layout-color-card-image`, `layout-split-color`), the visual mass of the two columns must approximately balance. A 5-item column next to a 1-stat column reads as half-empty regardless of how strong the stat is, and a 4-item column next to a 4-paragraph column with a tall coral card reads imbalanced when the items end at 50% canvas height while the card fills 100%.

Three escape hatches when columns don't naturally balance:

1. **Equalize content density.** If the lighter column has three units, lift it to four — or compress the heavier side to four. The cleanest fix when both sides have flexible content.
2. **Vertical-center the lighter column** (`align-self: center` instead of top-aligning). The empty space then sits as breathing room above AND below, not as a hole at the bottom.
3. **Add one supporting element** to the lighter column — a coral-rule + one-line key phrase, a small spike-mark divider, a footnote-style caption. The element must carry meaning. Never filler ("자세한 내용은 다음 슬라이드에…", "more details to follow").

Inverse rule: if both columns are full but unevenly full (A ends at 70% height, B ends at 100%), do NOT pad A with empty `<div>`s. Either accept the asymmetry as deliberate (some Claude-style editorial layouts read better unbalanced) or trim B.

### Edge alignment — shapes and adjacent text share horizontal lines

This rule complements column balance. Balance is about MASS (total visual weight per column). Edge alignment is about LINES (the implied horizontal lines created where one element ends and the next begins).

When a decorative shape (card, color block, image, photo) sits in a layout next to a text column, the shape's **top edge must align with the first content element's top in the adjacent text column**, and the shape's **bottom edge must align with the last content element's bottom**. The eye reads aligned horizontal lines as intentional composition; floating misaligned edges read as oversight, even when the page otherwise looks "balanced."

Example failure: a coral callout card with `align-self: center` next to a 5-item checklist. The card centers in its grid track (which sizes to the checklist), so the card top sits *below* the first checklist item's top text and the card bottom sits *above* the last item's bottom text. Two new horizontal lines appear where there should be zero — the card visually floats and the slide reads as half-finished, even though the column-balance rule looks satisfied.

Three patterns that achieve edge alignment:

1. **Stretch the shape to the column's vertical span.** Remove the `align-self: center` override so grid `align-items: stretch` (the default) takes over. Inside the shape, distribute content with `justify-content: space-between` (focal at top, supporting at bottom) AND **fill the middle with meaningful content** (sub-stats, secondary divider + caption, supporting bullets). An empty middle between focal-top and aux-bottom is the orphan pattern banned by "Cards: focal block stays compact" — stretch + fill, not stretch + empty.
2. **Hard-set the shape height** to match the measured column height. Use this when the shape needs intrinsic aspect ratio (a 16/9 photo) and stretching would distort it.
3. **Top-align the shape and accept the column extends below it.** Acceptable when the shape is genuinely shorter and the visible empty space *below* the shape reads as deliberate breathing room. The column's bottom must still anchor to the slide's padding edge — never float halfway.

#### Paired anchored columns must share their bottom (and top) anchor lines

In `layout-split-color`, `layout-two-tone`, and similar paired layouts, when one column anchors content with `justify-content: space-between` and the other anchors with `margin-top: auto`, the resulting bottom anchors may not share the same horizontal line. The most common cause: **differing bottom (or top) padding values between the two columns**. A 80px / 64px padding mismatch produces a 16px disagreement at the bottom — small enough to look "almost right," large enough to register as wrong.

Fix: equalize bottom padding values between the paired columns. The bottom anchors must coincide on the same Y. The same applies to top anchors when both columns start with content (eyebrow rows, brand-marks). When designing a paired-column layout in `base.css`, pick one padding tuple and apply it to BOTH `.lhs` and `.rhs` — do not let them drift.

#### General invariant

Whenever two elements sit in adjacent columns of a split layout (or anywhere on a slide where they create implied horizontal lines), audit those lines. **Every misalignment ≥ 8px reads as oversight.** The composition fix is almost never to add more content — it is to make the existing edges share Y-coordinates.

#### Inset compensation when edges and text bounds differ

A column container's edges (top/bottom) and its text glyph bounds (first-line top, last-line bottom) are not the same Y. Standard line-height insets push the first text glyph ~3-5px below the container top for body type, and a list's last item often carries `padding-bottom` that pushes the container bottom 12-16px below the last text glyph.

When a decorative shape next to such a column stretches to the grid track height, the shape's color-field edges land on the *container edges* — not the *text edges* the eye actually compares. Two new misalignment lines appear: 4px above first text top, 14px below last text bottom.

Compensate explicitly:

```css
/* Remove trailing padding on the last list item so container-bottom = text-bottom */
.checklist .item:last-child,
.steps .step:last-child {
  padding-bottom: 0;
  border-bottom: none;
}

/* Decorative card next to a text column: small margin-top to match first-text inset */
.card.card-row-aligned {
  margin-top: 4px;   /* empirical for 16-18px body, line-height 1.4-1.55 */
}
```

The 4px figure is empirical and depends on the specific font and line-height. **Always render and measure** rather than guessing — the eye catches a 6px residual drift just as fast as a 16px drift.

### Spacing rhythm — uniform gaps via fixed tokens, not auto-fill outliers

A slide composes when its visible vertical gaps follow a recognizable rhythm. The eye reads "this is intentionally laid out" when all major gaps share a similar size, or when gaps follow a clear hierarchy (intra-group: small, inter-group: medium). When *one* gap is sized arbitrarily — because `margin-top: auto` absorbed leftover column space, or because `justify-content: space-between` had to redistribute a huge surplus — the rhythm breaks.

Two patterns produce outlier gaps:

1. **`margin-top: auto` next to fixed-gap siblings.** All siblings share `gap: 28px`, but a footer with `margin-top: auto` absorbs ~90px of leftover column space. Result: 4 normal 28px gaps + 1 inflated ~118px gap. The footer feels "exiled to the bottom" instead of "concluding the column."
2. **`justify-content: space-between` with disparate group heights.** Three groups summing to 250px in a 720px column produce ~235px inter-group gaps. The inter-group gap (235) is many times larger than any padding or intra-group gap (~32). The slide reads as inflated.

Diagnostic: **if any single gap on a slide is more than 2× the next-largest gap, the rhythm is broken.** That outlier gap is what the eye flags.

Fixes (pick the one that matches intent):

- **Replace `margin-top: auto` with `justify-content: space-between` on the column.** Instead of one auto-fill outlier, the leftover space distributes across *all* gaps — uniform but slightly larger than the original `gap` value. Acceptable only if group sizes are comparable; if some groups are much heavier than others, the inter-group gaps still inflate.
- **Compute a fixed gap that fills the column.** If column inner height is 560 and content totals 358, set `gap: calc((560 - 358) / 4)` for 4 inter-element gaps of ~50px. Brittle but precise.
- **Add a meaningful element that absorbs the surplus.** A key-principle line, a divider with caption, a secondary stat. The element must carry meaning — never filler ("more details to follow").
- **Accept that the column is shorter than the canvas allows.** Stack content with fixed `gap: 28px` from the top, leave the bottom of the column as deliberate breathing room. This is the right answer when the column genuinely has nothing more to say.

`justify-content: space-between` is NOT banned — it is the correct fix when groups are comparably sized and you want all gaps uniform. The ban is on `margin-top: auto` next to fixed-gap siblings, because that *guarantees* one outlier gap.

### Cards: focal block stays compact

Inside a card, the focal element (big number, big quote, callout headline) and its supporting copy must read as one block. Do NOT use `margin-top: auto` to push a single auxiliary line to the card's bottom edge while the middle goes blank — the eye reads "empty card" and skips the focal.

The pattern to avoid:

```
┌──────────────────┐
│ TIME TO READY    │
│ 5분              │
│ 안에 점검 끝.     │
│                  │
│                  │   ← orphaned middle, no content
│                  │
│ 설치가 어려우면… │   ← orphaned bottom (margin-top: auto)
└──────────────────┘
```

The pattern to use:

```
┌──────────────────┐
│ TIME TO READY    │
│ 5분              │
│ 안에 점검 끝.     │
│ ──────────────── │   ← divider keeps the eye moving
│ 설치가 어려우면… │   ← supporting line directly under the divider
└──────────────────┘
```

If the card is genuinely taller than the content needs (e.g. forced height to match a sibling card), choose ONE:

- Shrink the card to fit its own content and let the sibling balance via the column-balance rule above
- Genuinely fill the middle with a meaningful unit (secondary stat, divider + caption, supporting quote) — three units of meaning, not one stat orphaned at top and one caption orphaned at bottom

### Pre-ship audit — "every visible element earns its place"

Before shipping a slide, audit each visible element and ask: **if I deleted this, would the slide still communicate the message?** If yes, delete it. Editorial composition is achieved when nothing remains to be removed, not when every corner is filled.

Common deletion candidates that production decks accumulate:

- Top-corner operational labels (`총 9시간`, `Updated 2026-05`, internal version stamps, `Slide 14 / 32`)
- Bottom-corner next-slide pointers on dividers (`다음 → 2차시`)
- `brand-mark` repeated on every slide — the cover, dividers, and closer are enough; body slides do not need a brand-mark unless the slide IS a cover or divider
- `eyebrow-row` AND `brand-mark` stacked at the top of one slide — pick one
- A `footer-row` hairline below a slide that has nothing new to add — the hairline alone reads as visual noise

## Anti-patterns (do NOT)

- **Do not hand-code coordinates** in the build script. Layout lives in CSS only.
- **Do not use python-pptx** for writes — it corrupts shapes (memory rule). Read-only inspection OK.
- **Do not embed slides as a single image** — user explicitly requires editable text/shapes.
- **Do not show page numbers** anywhere on the slide. (Reinforced above.)
- **Do not use Pretendard / Noto Sans KR** unless the user asks. Use font_discovery.py.
- **Do not use gradients** if the design.md's Don't section forbids them (check `guardrails.json`).
- **Do not write Korean strings via the Edit tool inside JS source files** — JSX/JS often mangles them. Author Korean directly inside the HTML files (UTF-8) or extract to JSON with `\uXXXX` escapes (global rule).
- **Do not split a multi-section deck into multiple PPTX files** without confirming first — one combined `.pptx` is the default (see "Output convention" above).
- **Do not pin every slide to the canvas color.** Use the design.md's surface tokens — see "Composition layers / Surface rotation rhythm" above.
- **Do not write helper text inside screenshot slots.** Empty grey frames only — see "Voice and copy rules" above.
- **Do not ship a deck whose entire body is on one canvas color** with only black text and hairlines. The reference templates this skill is calibrated against (AQUA, EcoSport, navy/cream business, Prezfull) explicitly avoid this — every slide composes. A 60-slide deck with 60 white-canvas + black-text + hairline slides is a regression.
- **Do not produce a 100% solid brand-color slide with white text and no contrast layer** (image, shape, or scrim). A flat brand-color rectangle reads as a banner ad, not a slide.
- **Do not use opacity ornamentally.** Alpha layers belong on photos (scrims), behind text (anchor blocks), and on cards over tinted canvases. Random transparent shapes in a corner are decoration; the skill rejects decoration.
- **Do not repeat the same composition pattern across consecutive slides** (photo+band → photo+band → photo+band reads monotonous even when the photos differ). Rotate compositions as aggressively as surface modes.
- **Do not use stock "innovation" photography** (smiling professionals pointing at laptops, abstract glow gradients, generic neural-network visuals). Subject-matter photos with editorial value only — see "Photos and imagery" above.
- **Do not stack 4+ textual elements on a cover or section divider.** Three maximum: one identifier, one headline, one supporting line — see "Cover and section-divider economy" above. `brand-mark + eyebrow + headline + subhead + bottom-left caption + bottom-right caption + corner badge` is six elements; the headline loses.
- **Do not write a footer-row that recaps what the body already shows.** Cards saying `1차시 / 2차시 / 3차시` do not need `총 3차시 · 약 9시간` underneath. Footer-rows carry new information or get deleted entirely (hairline included).
- **Do not let one column of a split layout sit half-empty.** A 5-item column next to a 1-stat column is half-empty regardless of how strong the stat is. Equalize density, vertical-center the light side, or add ONE meaningful supporting element — never filler text — see "Column balance in split layouts" above.
- **Do not use `margin-top: auto` to orphan a card's auxiliary line at the bottom while the middle goes blank.** The eye reads "empty card" and skips the focal. Either compress the card or genuinely fill the middle — see "Cards: focal block stays compact" above.
- **Do not let a shape's edges float misaligned with the adjacent text column's first/last content edges.** A coral card with `align-self: center` next to a 5-item checklist creates two new horizontal lines the eye reads as "almost-finished." Stretch the shape (and fill its middle), hard-set its height, or top-align it and accept the column extending below — see "Edge alignment" above.
- **Do not let paired columns of a split layout disagree on bottom (or top) padding.** A 80px/64px mismatch produces a 16px anchor drift at the bottom — small enough to look almost-right, large enough to register as wrong. Equalize padding values across `.lhs` and `.rhs` in `base.css`.
- **Do not mix `margin-top: auto` with fixed-gap siblings in the same column.** It guarantees one outlier gap (the auto-fill) ≫ the fixed gaps. The eye flags it. Either use `justify-content: space-between` on the column (distributes leftover across all gaps), compute a fixed gap that fills the column, or add a meaningful middle element. See "Spacing rhythm" above.
- **Do not let a list's `:last-child` keep its `padding-bottom` when a decorative card stretches alongside it.** The card bottom lands at the container bottom; the list's last text glyph sits 14px above that. Two new misalignment lines. Strip `padding-bottom` from the `:last-child` (and add 4px `margin-top` to the card) so edges meet text bounds — see "Inset compensation" above.
- **Do not ship based on browser screenshots alone.** The deliverable is the `.pptx`, and PowerPoint renders Korean text with whatever fallback font the client has installed (typically Malgun Gothic, ~10–15% wider glyphs than Gmarket Sans / Pretendard / SUIT). Card body text that wraps cleanly to 2 lines in `screenshots/slide-NN.png` will overflow the card's right edge in PowerPoint — the screenshot cannot reveal this. Always run Stage 2 of Phase E (build PPTX → export PDF → render → compare) before declaring a batch done. See "Phase E — Verify" above.
- **Do not auto-wrap body text in cards or columns < 400px wide.** Auto-wrap re-flows under PowerPoint's wider fallback fonts, so a comfortable 2-line wrap in browser becomes an overflow in PPTX. Hard-break the text with `<br>` at meaning boundaries at authoring time — each line's content is then frozen and survives font fallback. See "If body text sits in a card OR a column narrower than ~400px" in Phase C.
- **Do not let sibling cards have mismatched body line counts.** Three side-by-side cards with bodies of 3/3/2 lines (or 2/3/2) destroy the grid rhythm. Rewrite the odd-one-out's prose to match the others' line count. Line-count matching is a design constraint, not a "if convenient" preference.
- **Do not decorate body slides with infographics that have no structural data.** An infographic where the radial segments contain text fragments unrelated to each other is a styled bullet list. Use a real bullet list or grid. See "Infographics — use when structure is the message" in Phase C.
- **Do not exceed 7 nodes in a single infographic.** Past 7, the eye cannot parse the structure at a glance — the infographic's speed advantage disappears. Switch to a table or split across two slides.
- **Do not mix two infographic patterns on one slide** (e.g. a pyramid + a venn side-by-side). One structural metaphor per slide; the comparison itself becomes the noise.
- **Do not apply 3D for visual variety alone.** 3D pyramids and 3D bars are allowed ONLY when the visual weight of the shape carries the argument (hierarchy depends on foundation, volume implies magnitude). Flat information with 3D applied is decoration. See "3D variants — allowed when weight is the message" in Phase C.
- **Do not use CSS 3D transforms (`transform: rotateX/Y/Z`) for 3D shapes.** They render correctly in the browser but flatten on html2pptx export. Author 3D as SVG polygons (front rect + top parallelogram + right parallelogram per tier) — those survive as native PowerPoint shapes.
- **Do not import infographic templates as raster images** when they are authored by us. A pasted PNG of a "perfect" infographic is uneditable in PowerPoint and a regression. Build infographics as native shapes (`<div>`/SVG) so html2pptx converts them to editable shapes. Stock photo illustration (for `infographic-narrative-stat`) is the exception — there, an `<img>` is correct because the goal is a photographic asset, not a diagram.
- **Do not mix inconsistent column headers in pictogram-bar.** All columns share the same callout format (same shape, same typography); only the color differs between accent and non-accent. Plain-text header on column A + callout box on column B reads as oversight. See "If INFOGRAPHIC slide" guardrail.
- **Do not let infographic visual units fall outside the 720px canvas.** Roadmap nodes with vertical stagger, pyramid tiers with depth offset, narrative-stat illustrations — all must verify the lowest pixel of the lowest element fits inside the bottom-bar's start. Don't trust browser scroll-overflow to hide the bug; the PPTX will clip without warning.

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

/* Full-bleed dark / brand-color slide — REQUIRED pattern */
/* Do NOT use `body { background-image: url(...) }` or */
/* `<section style="background-image:url(...)">` — html2pptx silently drops them */
/* and the slide background falls back to the canvas color. */
.slide.fullbleed-dark { padding: 0; position: relative; }
.slide.fullbleed-dark > .bg-layer {
  position: absolute; inset: 0;
  background: var(--c-surface-dark);  /* solid color — always renders as a real shape */
  z-index: 0;
}
.slide.fullbleed-dark > .fg-layer {
  position: relative; z-index: 1;
  width: 1280px; height: 720px; padding: 64px 96px;
  color: var(--c-on-dark);  /* class-based cascade — survives html2pptx */
  display: flex; flex-direction: column; gap: 28px;
}
/* Authoring example:
<section class="slide fullbleed-dark">
  <div class="bg-layer"></div>
  <div class="fg-layer">
    <h1 class="t-display-hero">개념은 잡혔다.<br>다음은 손의 시간.</h1>
  </div>
</section>
*/
```

If a new component needs a non-stretching badge inside a row-flex parent, no extra rule needed (`align-self` is no-op on the cross axis there).

## PowerPoint compatibility hardening (lessons from production)

PowerPoint applies its own font fallback (e.g. Malgun Gothic when SUIT/Gmarket Sans/Pretendard isn't installed in the client's PowerPoint font path) and re-measures text boxes. This causes the last character of a single-line text to wrap to a new line, or card body text to overflow its container horizontally. Seven-layer defense baked into this skill:

1. **`scripts/html2pptx.js` — single-line width buffer 10%** (was 2%). Every single-line text box is recorded `max(width × 1.10, width + 24px)` wider than measured, absorbing the metric drift between browser font and PowerPoint fallback font.
2. **`scripts/html2pptx.js` — explicit `wrap` per box.** `wrap: !isSingleLine, autoFit: false`. Multi-line boxes wrap inside the box (so card body text can't overflow vertically); single-line boxes never wrap (so a short button label stays on one line, regardless of fallback metric).
3. **CSS-side hard locks** — `width: max-content; min-width: 120px; white-space: nowrap` on every CTA/badge/brand-mark. For multi-line card body text, give it explicit `width` AND `height` so html2pptx classifies it as multi-line.
4. **Authoring-time `<br>` at meaning boundaries** — for any body text inside a card or column narrower than ~400px, hard-break the lines yourself. Each line's content is then fixed at authoring time and survives PowerPoint's re-measurement under fallback fonts. See the "If body text sits in a card OR a column narrower than ~400px" guardrail in Phase C.
5. **NEVER use `background-image: url(...)` on `<section>` or `<body>`.** html2pptx does NOT translate this to a PowerPoint slide background. The slide background falls back to the canvas color (e.g. `#F7F4ED` cream) and the linked PNG is silently dropped — `ppt/media/` ends up missing the file entirely. If the slide is supposed to be dark, the canvas-cream slide background combined with `color: var(--c-on-dark)` (≈ `#FCFBF8`) produces **white text on cream** — invisible. **Only `<img>` tags become PowerPoint native images**; section/body bg-image does not. *Production incident: an entire 131-slide deck had 5 hero-dark slides rendered as cream-with-invisible-text because the dark background was authored as `body { background-image: url(...) }` instead of a div + class.*
6. **Dark / colored surfaces must be a `<div>` shape inside the slide, not a `<section>` / `<body>` background.** Use `.slide.dark { background: var(--c-surface-dark); color: var(--c-on-dark); }` (the class on `<section>` works because html2pptx lays a single solid-fill rectangle for the canvas, but the canvas color is read from the body's computed background — so `.slide.dark` alone is *also* unreliable for full-bleed dark slides). The reliable pattern: a `position: absolute; inset: 0; background: var(--c-surface-dark);` div as the **first child** of `<section class="slide canvas">`, then place all foreground content as siblings on `position: relative; z-index: 1;`. That dark div becomes a real PowerPoint rectangle shape, the slide background underneath stays canvas (PowerPoint's default), and color cascades work because `<section class="slide dark">` keeps the class on the foreground content. See "Full-bleed dark / brand-color slide" in Critical CSS contracts.
7. **Avoid `style="color: var(--c-on-dark-XX)"` (rgba CSS variables) directly on text.** PowerPoint's solidFill maps the rgba to `<a:srgbClr val="FCFBF8"><a:alpha val="78000"/></a:srgbClr>` — the alpha *is* preserved, but on a slide whose background fell back to canvas-cream (because of layer-5 violation), 78%-alpha cream-on-cream is even harder to see than 100%-alpha cream-on-cream. Prefer class-based color cascade (`.slide.dark p { color: var(--c-on-dark-78); }` in base.css) or solid hex values. When you must inline, audit that the slide actually has a real dark layer underneath.

Layer 4 is the most reliable for narrow-column body text. Layer 2's `wrap: true` only prevents *vertical* overflow (text spilling below the card); it cannot prevent *horizontal* overflow when PowerPoint's wider fallback glyphs push a wrapped line beyond the box's right edge. Hard breaks bypass the problem entirely. Layers 5–6 are the most catastrophic if violated — they make entire slides illegible.

### Diagnostic workflow when production PowerPoint shows drift

When the user reports "PPTX와 스크린샷의 배치가 다르다" (PPTX layout differs from screenshots), run this diagnostic:

1. **Render the PPTX to PDF, then to PNG.** Export the `.pptx` to PDF (PowerPoint File→Export, or `soffice --headless --convert-to pdf`). Use the `pdf2png.py` snippet in Phase E to render each PDF page. This is what the user actually sees — the deliverable, not the browser.
2. **Compare PDF render against the browser screenshot side-by-side.** Identify whether the issue is:
   - **Layout drift** (boxes at different Y/X positions) — investigate base.css or html2pptx measurement
   - **Content drift** (text inside correctly-positioned boxes overflows or rewraps) — apply layer 4 (`<br>`) to the affected text
3. **Confirm with `debug-positions.js`** (snippet in Phase E). If `getBoundingClientRect()` measurements match the layout you intend, html2pptx is faithful and layer 4 is the right fix. If browser positions are wrong, fix the CSS instead.

Common symptom phrases and their fix layers:

| Symptom | Layer to apply |
|---|---|
| 마지막 글자만 다음 줄로 떨어지는 사고 (single-line tail wraps) | Layer 1 (already in html2pptx) — verify CSS uses `white-space: nowrap` |
| 카드 본문이 카드 밖으로 흘러나가는 사고 (card body overflows right) | Layer 4 — hard-break body with `<br>` at meaning boundaries |
| 텍스트가 맥락 단위로 안 나뉘고 어색하게 끊김 (text doesn't break at meaning boundaries) | Layer 4 — same fix; this is the same symptom from a different angle. PowerPoint's fallback font reflows your auto-wrapped lines into nonsense breaks. Hard-break with `<br>` at clauses |
| dark 슬라이드인데 글씨가 흰색이라 안 보임 / 캔버스가 cream으로 떨어짐 (dark slide renders as cream canvas with invisible white text) | Layer 5 + Layer 6 — `body { background-image: url(...) }` and `<section style="background:transparent;background-image:url(...)">` were silently dropped. Replace with absolute-positioned dark `<div>` as first child of the section |
| 다크 영역의 본문 색이 어둡게 가라앉음 / 알파가 다르게 보임 (rgba color appears different in PowerPoint) | Layer 7 — move the color from inline `style="color:var(--c-on-dark-XX)"` to a class-based rule in base.css; or use a solid hex |
| `ppt/media/` 폴더에 우리가 만든 PNG가 없음 (custom PNGs missing from PPTX media folder) | Layer 5 — section/body bg-image is the cause. Only `<img>` tags become embedded images |
| 컬럼 사이 하단 정렬이 어긋나는 사고 (paired columns misalign at bottom) | base.css — equalize bottom padding across `.lhs` and `.rhs` |
| 텍스트 박스 위치는 맞는데 글꼴만 달라 보이는 차이 (correct boxes, different glyphs) | Accept — fallback rendering only, no structural fix needed |

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
│   ├── base.css                  ← tokens (CSS variables incl. --c-primary-rgb + --alpha-*), text classes, components
│   └── components/
│       ├── hero.html                       ← body-density backbone (6)
│       ├── data-callout.html
│       ├── feature-grid-3up.html
│       ├── pipeline-diagram.html
│       ├── compare-table.html
│       ├── cta-banner.html
│       ├── layout-split-color.html         ← layered compositions (6)
│       ├── layout-photo-band.html
│       ├── layout-color-card-image.html
│       ├── data-callout-diagonal.html
│       ├── team-photo-circles.html
│       ├── quote-overlay.html
│       ├── infographic-radial-process.html       ← infographic patterns (7)
│       ├── infographic-hierarchy-pyramid.html
│       ├── infographic-hierarchy-pyramid-3d.html
│       ├── infographic-quadrant-diamond.html
│       ├── infographic-pictogram-bar.html
│       ├── infographic-roadmap-spatial.html
│       └── infographic-narrative-stat.html
├── references/
│   └── alignment-guardrails.md   ← anti-patterns + why
└── examples/
    └── linear-rag-deck/          ← reference 6-slide deck (Linear DESIGN.md)
```

## Required dependencies

In the workspace (not the skill itself — workspaces own their `node_modules`):
- Node.js: `pptxgenjs`, `playwright`, `sharp`
- Python: `playwright`, `python-pptx` (read-only), `pyyaml`, `pymupdf` (Phase E Stage 2 PDF→PNG)

Install once per workspace:
```
npm i pptxgenjs playwright sharp
pip install playwright python-pptx pyyaml pymupdf
python -m playwright install chromium
```

## Output

`output/<deck-name>.pptx` — fully editable, brand-consistent, alignment-verified.
