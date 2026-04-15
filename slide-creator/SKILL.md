---
name: slide-creator
version: 2.1.1
description: "Create presentation slide decks as HTML and auto-export to 16:9 PDF. Use when the user asks to make a PPT, slide deck, presentation, or pitch deck. Final output is a PDF file — not PowerPoint format."

metadata:
  starchild:
    emoji: "🎞️"
    skillKey: slide-creator
    install:
      - kind: pip
        package: playwright
      - kind: pip
        package: PyMuPDF

user-invocable: true
---

# Slide Creator — HTML → PDF Presentations

Build slide decks as HTML, export to pixel-perfect 16:9 PDF via headless Chromium.

**Output format: PDF** — not Microsoft PowerPoint (.pptx). The PDF preserves exact layout, fonts, and colors across all devices.

## Why HTML → PDF

- CSS layout (Grid/Flexbox) is far more flexible than any PPT editor
- Full web typography, gradients, SVG, animations (print degrades gracefully)
- Git-friendly, reproducible, scriptable
- One command → PDF with exact 16:9 page dimensions

## Workflow

### 0. Identify Scenario (new)

Before any other step, identify the presentation scenario. Read `references/content-scaffolding.md` for full templates.

| Scenario keyword | Template to use |
|-----------------|----------------|
| pitch / investor / 融资 | `pitch-deck` |
| conference / keynote / 大会 / 演讲 | `conference-keynote` |
| product launch / 发布会 | `product-launch` |
| report / research / 研究 / 报告 | `research-report` |
| (none of the above) | ask user which scenario fits best |

Each template defines: slide count, page titles, required content per page.

### 0.5 Bilingual Layout (if needed)

If the audience is bilingual (e.g. HK, Singapore, global Chinese conference), or the user mentions Chinese + English:
- Use the `bilingual` layout mode from `references/content-scaffolding.md`
- Heading: English (large) + Chinese subtitle (smaller, --text-muted)
- Body bullets: Chinese first, English parenthetical optional
- Avoid pure English-only decks for HK/TW/SG audiences

### 1. Plan the Deck

Define slide count and content per slide based on the scenario template. Each slide = one `<section class="slide">`.

### 1.5 Art Direction (run this before building)

> Run this step whenever the user hasn't provided a specific visual style.
> Read `skills/slide-creator/references/art-direction.md` for the full style taxonomy,
> CSS token templates, and style-brief output format.

**Step A — Ask 4 questions:**
1. 受众与场景：给谁看、什么场合（投资人/内部/公开演讲）？
2. 情绪关键词：希望观众感受到什么（专业权威 / 创意活力 / 亲切友好 / 极客酷炫）？
3. 品牌约束：有没有指定的品牌色、logo、字体？
4. 参考素材：有没有想对齐的模板参考（图片、网页链接、现有 deck 截图）？

**Step B — Generate a visual style picker page:**
Do NOT present style options as text descriptions — users can't evaluate styles from words alone.

Reference handling rules:
- If user provides **image files/screenshots**: sample palette (primary/surface/accent), inspect layout density, corner radius, typography tone from the visual.
- If user provides **web URLs**: use `web_fetch` to extract design cues. **Critical — follow this extraction protocol to avoid misreading the style:**
  1. **Ignore the brand name / domain name** — never infer visual style from the product's industry or name (e.g. "Neo" does NOT mean neon, "Opera" does NOT mean European luxury).
  2. **Read copy tone & vocabulary** — the words used on the page reveal mood (e.g. "surgical precision", "quiet confidence" → restrained; "unleash", "radically" → bold/aggressive).
  3. **Extract explicit color vocabulary** — look for CSS keywords in the fetched text, or color names mentioned in body text / alt tags. Warm vs cool, light vs dark, muted vs saturated.
  4. **Infer layout density** — count words per section; sparse = editorial/luxury, dense = technical/functional.
  5. **Identify decorative motifs** — mentioned or implied (e.g. geometry, gradients, photography, illustration, line art, brutalism).
  6. **Cross-check against art-direction.md** — find the closest matching template, then describe the delta (e.g. "Style G but warmer, replace blue with burnt orange, add subtle grid lines").
  7. **When uncertain**: be conservative — under-promise the style match and present 3 options where Option A is your best interpretation, B is safer/cleaner, C is more experimental. **Never confidently assert a style that contradicts the actual visual evidence.**
- If user provides both: prioritize image cues first, URL cues second.
- If no references are provided: use built-in style taxonomy defaults.

Then:
1. Create `output/style-picker/index.html` — a single page with 3 side-by-side mini slide previews (16:9 aspect ratio), each fully rendered with real CSS (colors, fonts, layout, decorative elements). Each preview must look like an actual slide, not a color chip.
2. Build these 3 options as: **(A) Reference-faithful**, **(B) Safer corporate variant**, **(C) Bolder creative variant**.
3. `preview_serve` the directory and show the preview URL.
4. Each card has a label below: style name + one-line description.
5. Add `onclick` highlight so the user can click to indicate their choice.

User picks by saying "选A" / "我要B" / "融合A+C" etc.

**Step C — Generate style-brief.md:**
Once user selects a style, write a `style-brief.md` (template in art-direction.md) in the project directory.
All subsequent HTML/CSS work must follow this brief.

**Step D — Ask for brand assets (logo / colors):**
After user picks a style, ask:
> "有没有 logo 或品牌色需要加进去？可以上传图片文件，我会把 logo 嵌入每张 slide。"

If logo uploaded: embed as base64 in HTML (use `base64.b64encode` in bash), place in top-left or top-right corner at ≤60px height.
If brand color given: override `--accent` in CSS token block with user's color.

### 2. Choose a Theme

If Art Direction was completed, the `style-brief.md` is the theme spec — skip this table.
Otherwise, use as a quick fallback:

| Style | Background | Accent | Font | Mood |
|-------|-----------|--------|------|------|
| Dark tech | `#000` / `#0a0a0a` | bright orange/blue/green | Inter, Space Grotesk | Bold, modern |
| Light clean | `#fff` / `#f8f8f8` | navy, teal, coral | Inter, DM Sans | Professional, minimal |
| Gradient | dark gradient | vibrant accent | Any sans-serif | Creative, energetic |
| Corporate | `#1a1a2e` / white | brand color | system fonts | Trustworthy, formal |
| Playful | soft pastels | warm pop colors | Nunito, Poppins | Friendly, casual |

### 3. Build HTML + CSS

Create a project directory with `index.html` + `styles.css`.

**Start from `assets/base.css`** — structural skeleton (slide dimensions, print rules, layout helpers) with NO colors or fonts. Layer your theme on top:

```css
/* Example theme layer — customize freely */
body {
  font-family: 'Inter', sans-serif;
  color: #fff;
  background: #000;
}
.slide { background: #0a0a0a; }
.slide-tag { background: rgba(0,120,255,0.15); color: #0078ff; }
.card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); }
```

**Mandatory structural rules** (in base.css — don't remove):

```css
.slide { width: 1280px; height: 720px; page-break-after: always; overflow: hidden; }
@page { size: 1280px 720px; margin: 0; }
```

**Key rules:**
- Use `px` units — never `vh/vw/rem/%` for slide dimensions
- Google Fonts: use `<link>` in `<head>`, export script waits for network idle
- Viewport meta: `<meta name="viewport" content="width=1280">`
- Content must fit within 720px height — overflow is clipped

### 4. Preview (Optional)

Use `preview_serve` to preview in browser before exporting.

### 5. Export to PDF

```bash
python3 skills/slide-creator/scripts/export_pdf.py --dir <project-dir> --output output/<name>.pdf
```

Options:
- `--dir` — directory containing `index.html` (required)
- `--output` / `-o` — output PDF path (default: `<dir>/deck.pdf`)
- `--width` — slide width in px (default: 1280)
- `--height` — slide height in px (default: 720)

### 6. Verify

The script prints slide count and confirms output path. Extra check:

```python
import fitz
doc = fitz.open("output/deck.pdf")
print(f"Pages: {doc.page_count}")
for p in doc:
    r = p.rect
    print(f"  {r.width*96/72:.0f}x{r.height*96/72:.0f}px")
```

## Style Guidelines

- **No default brand** — every deck gets a theme tailored to its content
- Prefer Art Direction-first workflow (questions → references → user pick → `style-brief.md`)
- Ask the user for preference: dark/light, accent color, font, mood
- Each slide should have clear visual hierarchy: tag → title → content
- Keep text concise — slides are visual, not documents
- Use `.bg-glow` with theme-colored radial gradients for depth
- 默认不使用 `web_search` 做风格检索；优先用户提供的参考图/链接 + `art-direction.md` 模板
- 当用户给了参考链接时，可用 `web_fetch` 读取页面内容提取设计线索（色调/语气/布局），但最终 CSS 仍由本地模板与变量落地
- When user asks for "美术建议/风格建议", always generate a visual style-picker preview page (3 options) — never use text descriptions alone
- Build HTML strictly against chosen style brief, then export PDF (do not skip brief unless user explicitly opts out)
- After style is chosen, always ask about logo / brand assets before building
- For HK/TW/SG/bilingual audiences, default to bilingual layout unless user says English only

## Style Microtweaks (after style is chosen)

If user says "主色改成红色" / "换个字体" / "圆角再大一点", do NOT restart art direction.
Instead, directly patch the `--accent` / `--font-head` / `--radius` CSS variable in `styles.css`.
Only restart art direction if user wants a completely different style.

## Gotchas

- **Chromium deps**: first run needs `python3 -m playwright install chromium && python3 -m playwright install-deps chromium`
- **Fonts**: Google Fonts need HTTP — the export script starts a local server automatically
- **Emoji rendering**: headless Chromium may lack emoji fonts — use SVG icons instead
- **Large images**: embed as base64 or use relative paths (local server serves the project dir)
- **Slide overflow**: content exceeding 720px height is clipped — design within bounds
