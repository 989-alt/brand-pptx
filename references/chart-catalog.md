# chart-catalog — data-viz selection + starter components

The guide's biggest lever is **data visualization**: 23 of its 46 variants are charts. A data slide's visual *is* the chart — so when a chart, diagram, matrix, or table carries the slide, **do not add a decorative photo** (the data is the visual). This file is the "signal word → chart type" dictionary plus the chart rendering rules.

## How charts render through html2pptx (read first)

html2pptx turns `<div>` backgrounds into shapes and **drops inline `<svg>`**. So charts split into two rendering paths:

| Path | Charts | How | Editable in PPTX? |
|---|---|---|---|
| **CSS shapes** | bar (column), h-bar, bullet/progress, stat-4up | `<div>` bars with inline `height`/`width` % | ✅ yes — each bar is a native shape |
| **Native pptx chart** | line, area, donut, pie, scatter, … | `<div class="placeholder" id="…">` + sibling `slide-NN.charts.json` → `build_pptx.js` calls `slide.addChart()` | ✅ yes — native PowerPoint chart |

Both were verified end-to-end (browser + PowerPoint PDF render). **Never** author a chart as inline `<svg>` expecting it in the PPTX — the `<svg>` shows only in the browser preview (which is fine as a preview *inside* a placeholder slot).

### Ships as a component now

| Component | Variant | Path |
|---|---|---|
| `chart-bar.html` | GCB Column — one category over time; highlight current/last bar with `.bar.is-focus` | CSS shapes |
| `chart-hbar.html` | GHB Horizontal Bar — ranking with long labels; top row `.hbar-row.is-focus` | CSS shapes |
| `stat-4up.html` | N Stats 4-up — four KPIs as a dashboard | CSS + text |
| `chart-line.html` + `chart-line.charts.json` | GLN Line — single time-series trend | native |
| `chart-donut.html` + `chart-donut.charts.json` | GS Donut / GHG Half-Donut — one headline ratio, big % in center | native |

**Using the native-chart components:** copy both files and rename the sidecar to match the slide, e.g. `chart-line.html → slide-07.html` and `chart-line.charts.json → slide-07.charts.json`. The placeholder `id` in the HTML must match the `"placeholder"` field in the JSON. Edit the JSON's `data` (labels + values) and `options.chartColors` (brand hex, no `#`).

Sidecar format (`slide-NN.charts.json`):
```json
[{ "placeholder": "chart-line", "type": "line",
   "data": [{ "name": "MAU", "labels": ["1월","…"], "values": [12,"…"] }],
   "options": { "showLegend": false, "chartColors": ["5E6AD2"], "lineDataSymbol": "none" } }]
```
`type` is any pptxgenjs ChartType (`line` · `area` · `bar` · `pie` · `doughnut` · `scatter` · `radar`). The placeholder rect supplies `x/y/w/h`; `options` overrides everything else.

## Signal word → chart (condensed from the 23 Data-Viz variants)

| Your data sounds like… | Chart | Code | Notes |
|---|---|---|---|
| 분기/월 매출, 한 카테고리 시간 흐름 | Column | GCB | last bar = accent |
| 항목명 긴 순위 (채널·기능 Top 5) | Horizontal Bar | GHB | label readability |
| 단일 시계열 추세 (MAU 12개월) | Line | GLN | 우상향 = 성장 스토리 |
| 누적 볼륨 (누적 가입자) | Area | GAR | 면적으로 볼륨감 |
| 단일 핵심 비율 강조 (86% 전환) | Donut | GS | 가운데 큰 숫자 |
| 목표 대비 달성 게이지 (72%) | Half-Donut | GHG | 가운데 % |
| KPI 실적 vs 목표 | Bullet | GBT | 목표선 한 줄 |
| 전체 구성비, 항목 ≤4 | Pie | GPI | 4개 초과면 Treemap |
| 항목 많은 구성비 (제품 Top 10) | Treemap | GTM | 면적=비중 |
| 두 집단 3지표 비교 (우리 vs 경쟁) | Grouped Bar | GG | |
| 구성 + 추세 동시 (분기 매출×제품군) | Stacked Bar | GSB | |
| 깔끔한 소수 랭킹 (팀별 OKR) | Lollipop | GLP | 막대보다 세련 |
| 여러 지표 추세 비교 (채널별 트래픽) | Multi-Line | GML | |
| 단위 다른 두 지표 (MAU 막대 + 성장률 라인) | Bar+Line | GL | |
| 두 지표 상관·역상관 (가입↑ CAC↓) | Dual-Axis | GDA | |
| 비율 인포그래픽 (100명 중 62명) | Waffle | GWF | 10×6 그리드 |
| 값의 분포 (결제액 분포) | Histogram | GHS | |
| 두 변수 상관 (가격 vs 만족도) | Scatter | GSC | 점 크기=3번째 변수 |
| 행×열 강도 (요일×시간 활성) | Heatmap | GHM | 색 진하기=강도 |
| SaaS 리텐션 (가입월×N개월) | Cohort Heatmap | GCH | 우하향 삼각형 |
| 큰 KPI + 미니 추이 | Sparkline | GSP | 숫자 카드 옆 |
| 시장 규모 계층 (TAM/SAM/SOM) | Bubble | GB | 동심원 |
| 투자/비용 분포 | Investment Donut | PD | 도넛 + 범례 |

Non-`G` data-bearing archetypes from the catalog: **N** Stats 4-up · **NF** Financial Forecast (KPI cards + trend) · **P** Pricing Tiers · **W** SWOT 2×2 · **V/VQ** Positioning/Quadrant · **BR/R** Comparison/Ranking rows.

## Chart styling rules (from the guide)

- **Highlight the focal element** — the current quarter, the winning bar, the answer — in the brand accent; everything else stays muted (`--alpha-brand-soft`). One focus per chart.
- **Pie ≤ 4 slices.** More than four → Treemap (area is easier to compare than thin wedges).
- **The chart is the visual** — no background photo on a chart slide.
- **One headline per chart.** The title states the takeaway ("4분기에 곡선이 꺾였다"), not the chart type ("분기 매출 막대그래프").
- **Label the axis or the bars, not both** when space is tight.
- Numbers carry units (`₩5.2억`, `48K`, `127%`) — see copy-guide rules in SKILL.md.

## Roadmap (documented, not yet a component)

Grouped/Stacked Bar, Multi-Line, Area, Scatter, Heatmap, Cohort Heatmap, Waffle, Bubble, Treemap, Bullet, Lollipop, Half-Donut, Bar+Line, Dual-Axis. Most reach the deck fastest via the **native-chart sidecar** path (add a `placeholder` + a `charts.json` entry) — only bar-family variants need new CSS components.
