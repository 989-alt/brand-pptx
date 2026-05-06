# Example: Linear-styled RAG intro deck

A 6-slide deck generated from `design.md` (Linear's design tokens) on the topic
"RAG는 LLM 환각을 싸게 잡는 조립 라인이다."

## Files
- `design.md` — Linear DESIGN.md (input)
- `output.pptx` — generated, fully editable PowerPoint (105 native text frames + 64 native shapes)
- `screenshots/slide-NN.png` — Playwright renders used for alignment verification

## How it was built
1. `parse_design_md.py design.md` → tokens.json + guardrails.json (dark canvas, no gradients)
2. `font_discovery.py` → matched Gmarket Sans (Korean, "geometric-modern" tone) + Cascadia Code (mono)
3. Authored 6 HTML slides using `templates/components/*.html` (hero, data-callout, feature-grid-3up, pipeline-diagram, compare-table, cta-banner)
4. `build_pptx.js --slides slides --out output.pptx` — html2pptx
5. `screenshot_slides.py` → PNG verification, all 6 slides confirmed alignment-clean
