# sensory-finish — 감각적 완성도 playbook

The target is the polish level of the MiriCanvas reference decks in `aesthetic-targets/`: layered depth, frosted glass cards, soft floating chips, gentle brand-tinted surfaces, pill labels, bold data callouts, timeline/connector motifs. **This is a quality bar, not a fixed look.** The treatments are expressed in **each design.md's own colors and tone** — never forced into baby-blue glass.

## The two rules that keep it from going wrong

1. **Express the finish through the brand's tokens, at the brand's saturation.** A dark Linear deck gets depth from its surface ladder + hairlines (glass veils are near-invisible there, and that's correct); a light/consumer deck gets prominent frosted-white cards + soft shadows + brand-tinted surfaces. `parse_design_md.py` emits mode-adaptive `--glass-fill`/`--glass-border` so the same class self-tunes.
2. **Gate every treatment on `guardrails.json`.** If the design.md's Don't list forbids gradients or shadows (Linear: *"resists drop shadows," "no atmospheric gradients"*), drop those treatments and lean on the brand's own depth language. Importing glassmorphism onto a system that rejects it is a regression, not an upgrade.

## Treatment → class → mode adaptation → PPTX degradation

All classes are html2pptx-safe (verified in browser **and** PowerPoint PDF render). The browser screenshot shows the full effect; PowerPoint approximates as noted.

| Treatment | Class | Light deck | Dark deck | In PowerPoint |
|---|---|---|---|---|
| Frosted card | `.glass-card` (`.on-color` on brand canvas) | prominent white-90% veil | subtle white-8% veil | translucent fill + border + soft shadow render; **backdrop-blur is dropped** (browser-only) — degrades to a clean translucent panel |
| Soft-3D chip | `.icon-tile` (`.solid`) | tinted/solid chip + shadow | same, subtler | fill + radius + shadow render; put an `<img>` glyph inside (inline `<svg>` is dropped) |
| Pill label | `.pill` (`.solid` / `.tag`) | brand-soft / solid | same | rounded shape + text render exactly |
| Big number | `.t-stat` / `.t-stat-sm` (+ `.unit`) | brand color | brand color | renders exactly (text) |
| Timeline | `.timeline` + `.timeline-dot` + `.timeline-line` | brand dots/line | brand dots/line | dots + line render; on a brand canvas override to white |
| Soft shadow | `.soft-shadow` / `.float-shadow` (or `--shadow-soft`) | yes | only if guardrails allow | outer box-shadow → native pptx shadow (inset dropped) |
| Tinted surface | `.surface-brand-tint` (solid rgba) | yes | yes | renders as a translucent shape |

Only effective when the `<div>` also has a background or border (a shadow-only div is not emitted as a shape).

## Gradients: never CSS — rasterize to PNG

html2pptx **throws** on `linear-gradient`/`radial-gradient` (on `<body>` and on any `<div>`). For a brand-gradient cover/summary surface, pre-rasterize a PNG with Sharp and set it as the **body** background image (body images become the slide background):

```js
// make-grad.js — run in the workspace, then: body { background-image: url('assets/grad.png'); }
const sharp = require('sharp');
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#5e6ad2"/><stop offset="1" stop-color="#3a429e"/>
  </linearGradient></defs><rect width="1280" height="720" fill="url(#g)"/></svg>`;
sharp(Buffer.from(svg)).png().toFile('assets/grad.png');
```

If gradients are forbidden by guardrails, use a **solid brand canvas** (as `summary-band.html` does) — frosted white-veil cards + soft shadows on a flat brand fill already read as premium. Verified: `summary-band` on a solid brand canvas renders cleanly in PowerPoint.

## Frosted glass that actually reads in PPTX (opacity recipe)

`backdrop-filter` blur is browser-only — in PowerPoint the frost comes entirely from **translucency over a gradient**, not blur. So two things must both be true or the card just looks like a flat white box:

1. **The card sits over a gradient/colored background** (a Sharp-rasterized PNG on `<body>`, or a saturated brand canvas). Over flat white there is nothing to frost.
2. **The card fill is genuinely translucent — about `rgba(255,255,255,0.60–0.68)`**, with a bright rim border `rgba(255,255,255,0.8)` and a soft shadow. `0.90+` is too opaque (reads as a solid card); below `~0.55` text legibility drops. The Eboki deck uses `0.62` and the gradient shows through in both browser and the exported PPTX. On a light gradient the frost is subtle; on a saturated band it reads as tinted glass — both correct.

`parse_design_md.py` emits `--glass-fill` per mode; for a glassmorphism-forward light brand, lower it toward `0.62` rather than the `0.90` default.

## Rich backgrounds: Sharp MESH first; stock photos for SUBJECTS, not backgrounds

A flat linear/radial gradient can look plain. The modern "rich" look is a **mesh gradient** — a base brand color with a few soft, heavily-blurred color blobs on top — still rasterized with Sharp so it's **exact to the brand color**:

```js
// mesh: base + blurred blobs → smooth modern gradient (regenerate bg-*.png, then rebuild)
const blob = (cx,cy,r,col,op)=>`<circle cx="${cx}" cy="${cy}" r="${r}" fill="${col}" opacity="${op}"/>`;
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720">
  <defs><filter id="b" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="85"/></filter></defs>
  <rect width="1280" height="720" fill="#2D5BFF"/>
  <g filter="url(#b)">${blob(200,110,440,'#7E97FF',.95)}${blob(1120,640,480,'#1733A0',.95)}${blob(990,120,340,'#4E6BFF',.7)}</g></svg>`;
require('sharp')(Buffer.from(svg)).png().toFile('workspace/images/bg-hero.png');
```

**Do NOT reach for stock photos as abstract backgrounds.** A `image_search.py "abstract blue background"` reliably returns the *wrong* blue (cyan/teal) and *busy* imagery (water droplets, bokeh) that destroys glass legibility — verified in practice. The mesh above gives a richer result on the exact brand hue with full control.

**Stock photos (`image_search.py`, Pixabay) are for SUBJECTS** — a laptop screen, a person in context, a product mockup on a text-driven slide (`hero`, `quote-overlay`, 2-column) — never the abstract canvas behind glass. Keep them on-palette and add a brand-tint scrim. (Also: Pixabay throttles burst downloads with an escalating 429 cooldown — fetch one image at a time, spaced out.) Full flow + manifest in `references/image-acquisition.md`; optional AI illustration via `scripts/image_gen.py` (needs `OPENAI_API_KEY`).

## Reference annotations (`aesthetic-targets/`)

The MiriCanvas references encode: (1) airy light-glass **cover** → dense saturated **summary** alternation; (2) every slide carries a visual — a 3D chip, a chart, a mockup, or a bold number; (3) pill-headed cards (개요·과정·결과); (4) a timeline with glowing dots; (5) oversized data callouts (127%, XX%). The `glass-cover` + `summary-band` components reproduce this pair in any palette. Reproduce the *structure and finish*, not the blue.

## Don't

- Don't import glass/shadow/gradient onto a system whose guardrails reject them.
- Don't use a CSS gradient anywhere (it throws) — rasterize to PNG or use a solid/translucent fill.
- Don't put a chart or icon as inline `<svg>` expecting it in the PPTX (dropped) — use a CSS shape, an `<img>`, or the native-chart placeholder path.
- Don't leave a glass card's bottom empty — fill it (pill / content / footer) like `summary-band`, or shrink it.
- Don't pin every slide to one solid brand color with white text and no contrast layer — that reads as an ad banner.
