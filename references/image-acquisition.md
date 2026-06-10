# image-acquisition — every slide's visual gets resolved before build

Adapted from ppt-master's image manifest + acquisition flow, but **free-first**: paid
AI generation is an optional upgrade, never a requirement. Each visual that isn't a
chart/diagram/CSS-shape is one row in a manifest, and **every row must reach a terminal
status before Phase D (build)** — no forgotten grey boxes.

## The free-first fallback chain (per asset type)

Pick by what the asset *is*, not a single linear order:

| Asset | 1st choice | fallback | last resort |
|---|---|---|---|
| **Abstract / gradient / mesh bg** | **Sharp MESH raster** (exact `--c-primary`; see sensory-finish) | AI gen (if key) | solid brand canvas |
| **Soft-3D icon / chip** | Sharp glossy badge (geometric) | AI gen (if key) — "isometric soft-3D icon" | flat `.icon-tile` |
| **Subject photo / product mockup** | **Pixabay** (free, on a *subject* — laptop/person/mockup) | AI gen (if key) | empty grey slot |
| **Procedure screenshot** | **empty grey slot** (user pastes their own) | — | — |

**Stock photos are for subjects, not backgrounds.** `image_search.py "abstract blue background"` returns off-tone (cyan) + busy imagery that ruins glass legibility — verified. Use Sharp mesh for the canvas behind glass; reserve Pixabay for a real subject on a text-driven slide.

**Free-first rule:** try Sharp (exact, free) and Pixabay (free) before AI generation. Only reach for `image_gen.py` when the user wants a rich illustration/photo *and* an API key is set. With no keys at all, every row still resolves (Sharp / empty slot) — the deck never blocks.

## The manifest (`workspace/images/image_prompts.json`)

```json
[
  { "filename": "bg-hero.png", "type": "background", "acquire_via": "sharp",
    "prompt": "radial blue gradient #2D5BFF", "aspect": "16:9", "status": "Rasterized" },
  { "filename": "cover-photo.jpg", "type": "photo", "acquire_via": "web",
    "query": "team collaboration office", "aspect": "landscape", "status": "Sourced" },
  { "filename": "hero-3d.png", "type": "icon", "acquire_via": "ai",
    "prompt": "isometric soft-3D blue cube, glossy, white bg", "aspect": "1:1", "status": "Generated" }
]
```

`acquire_via` ∈ `sharp | web | ai | slot | user`. `status` ∈ `Rasterized | Sourced | Generated | Slot | Needs-Manual`. **On acquisition failure: retry once, then mark `Needs-Manual` and continue — never halt the build.** A `Needs-Manual` row ships as an empty grey slot with a note to the user.

## CLI

```bash
# free stock (Pixabay primary; needs PIXABAY_API_KEY — free at pixabay.com/api/docs)
python scripts/image_search.py "blue gradient mesh" --filename bg-hero.jpg \
    --orientation landscape --min-width 1600 -o workspace/images

# optional AI generation (only if OPENAI_API_KEY set; else prints fallback guidance)
python scripts/image_gen.py "isometric soft-3D blue app icon, glossy, white bg" \
    --filename b-spark.png --aspect 1:1 -o workspace/images
#   or batch:  python scripts/image_gen.py --manifest workspace/images/image_prompts.json

# brand-exact gradients / soft-3D chips (free, no key) — author a small Sharp script
#   (see references/sensory-finish.md for the SVG→PNG recipe)
```

## License

Pixabay and Pexels content is **free for commercial use, no attribution required** — safe to embed in a client deck. The downloader rejects sub-`min` images (Pillow check). Keep photos on-palette (a blue brand → a blue photo) and text legible (scrim or keep text inside frosted cards).

## Placement

Downloaded/generated files live in `workspace/images/` and are referenced as
`<img src="images/<name>">` (or a `<body>` background) so html2pptx embeds them as
**native, replaceable PowerPoint images** — the Windows/Korean-path `file://` decode is
handled by `html2pptx.js` (`toLocalPath`).
