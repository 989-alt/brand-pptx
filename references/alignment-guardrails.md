# Alignment Guardrails — why each rule exists

Rules baked into `templates/base.css`. If you ever feel the urge to override one, re-read the corresponding "why" below first.

## 1. `html, body { width: 1280px; height: 720px; overflow: hidden; }`

`html2pptx` uses the body box as the slide canvas. If body sizes to content, slides crop or overflow.

## 2. `body { display: flex; flex-direction: column; }`

Prevents margin collapse between top-level slide sections — without it, a `<h2>` margin can leak through and shift everything down by ~20px in the converted PPTX.

## 3. `.slide { width: 1280px; height: 720px; padding: 64px; position: relative; }`

Locks the safe area. Top-bar / bottom-bar are positioned absolute against this; if `.slide` shrinks they collide.

## 4. `.badge, .btn-primary, .btn-secondary { align-self: flex-start; }`

Inline-flex elements (badges, buttons) inherit `align-self: stretch` from a column-flex parent and silently stretch to full container width. The fix is local: the element owns its sizing intent. Verified failure mode: slide-02 "잘못된 통념 #1" badge stretching across the slide before this rule was added.

## 5. `.eyebrow-row { display: inline-flex; align-items: center; gap: 8px; }`

The colored dot beside an eyebrow text must sit on the optical center of the cap-line. `inline-flex + align-items: center` does this for free; a manual top offset (e.g. `margin-top: 4px`) drifts whenever the font changes — and font_discovery.py is allowed to change the font.

## 6. Text only inside `<p>`, `<h1>`–`<h6>`, `<ul>`, `<ol>`

`html2pptx` requirement. Text directly inside a `<div>` collapses to ascii. Always wrap copy in a `<p>` even when there's only one line.

## 7. Backgrounds / borders only on `<div>`

Same reason: html2pptx maps `<div>` with a `background` or `border` to a native PowerPoint shape. Putting a background on a `<p>` produces an unstyled text frame.

## 8. Always set `min-height` on grid cells that may have ragged content

E.g. `.ct-cell { min-height: 64px; }` in the compare table. Without it, a row whose cells differ in line count produces uneven row heights, which in PPT looks like a misaligned table.

## 9. Use `grid-template-columns` for any A/B/C layout, never hand-coded x-coordinates

Grid distributes the available width exactly. The moment you write `left: 600px` you've broken the SKILL — fonts, language, and theme can all change content width.

## 10. Same-baseline rows: `display: flex; align-items: center;`

For rows like the success-row (badge + caption) or panel-head (dots + filename + version), every child must be a flex item; `align-items: center` does the optical alignment. Avoid `vertical-align` (text-only, doesn't apply to flex children).

## 11. Bottom-bar uses absolute positioning + `display: flex; justify-content: space-between;`

Caption (left) and tag (right) on a single baseline regardless of caption length. Don't use `text-align: right` on the tag — it leaves caption + tag at different baselines.

---

## Verification ritual (Phase E)

Render every slide as PNG @ 1280×720, device_scale_factor=2 (`scripts/screenshot_slides.py`). Open every PNG. Look specifically for:

1. Eyebrow dot vs eyebrow text — vertical center.
2. Badges — compact (text + ~10px padding), not stretched.
3. Grid columns — equal heights across the row.
4. Bottom-bar — caption + tag share one baseline.
5. Card content — top-aligned across cards in a 3-up grid.
6. Big number callouts — number baseline aligns with subhead's top text line, not with mid-baseline.

If you find drift, **fix the SKILL** (base.css or component template). Do not patch the individual slide.
