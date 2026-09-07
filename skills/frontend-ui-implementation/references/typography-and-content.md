# Typography and Content Implementation

Use the actual typeface and rendered browser output. Font metrics, available weights, language, viewport, and content density matter more than nominal `font-size` alone.

## Establish the type system

1. Inspect existing tokens and loaded font files. Never request a weight the font does not provide; synthetic bold/italic can alter hierarchy and metrics.
2. Set a readable root and let user zoom work. A practical web baseline is `1rem` body text when the root remains the browser default (normally 16 CSS px). This is an implementation starting point, not a WCAG-mandated minimum.
3. Use `rem` for user-scalable text, unitless line-height, and `clamp()` only where fluid scaling improves the actual composition. Do not make essential text smaller merely to fit.
4. Define a restrained semantic scale. The PDF proposes a modular scale from a 16px base with example ratios 1.25 (Major Third), 1.414 (Augmented Fourth), and 1.5 (Perfect Fifth). Treat these as generators, then round and compress the scale for small screens and product density.

```css
:root {
  --text-sm: 0.875rem;
  --text-base: 1rem;
  --text-lg: 1.25rem;
  --text-xl: clamp(1.5rem, 1.25rem + 1vw, 2rem);
  --text-display: clamp(2rem, 1.4rem + 3vw, 4rem);
  --leading-body: 1.5;
  --leading-heading: 1.15;
  --measure-body: 65ch;
}

body { font-size: var(--text-base); line-height: var(--leading-body); }
h1, h2, h3 { line-height: var(--leading-heading); text-wrap: balance; }
p, li { max-inline-size: var(--measure-body); }
```

The token names and values must follow the project when it already has a scale.

## Font-size and line-height principles

- Body text must remain readable at default zoom and at 200% zoom without clipping or two-dimensional scrolling for ordinary content.
- The PDF’s explicit starting bands are **1.0–1.4 line-height for headings** and **1.3–1.6 for general text**; its example is **16px × 1.5 = 24px**. Use unitless values so line-height follows font-size. Validate accents, diacritics, wrapped headings, and interactive labels before selecting the tight end.
- Smaller text and longer lines generally need more leading. Large display text can use tighter leading only when glyphs do not collide or clip.
- Landing-page text should not be made tiny to manufacture whitespace. PDF page 49 says to use a “big large font size” but supplies **no numeric size** in its text or illustration; do not invent one. Increase the base/display scale while preserving hierarchy and narrow-screen fit.
- Supporting text may be visually quieter, but never by combining tiny size, low contrast, and light weight.
- Controls inherit the application font and a readable size. Beware mobile browser zoom behavior on very small form text.

## Measure, alignment, and scanning

- The PDF cites **45–75 characters per line** and **50–60 characters** as source recommendations; start around `60–70ch` for sustained body reading, then inspect the real font and language. Labels, tables, code, and short marketing copy have different measures.
- Avoid justified web text when it creates uneven word spacing or reading rivers. Respect writing-mode conventions; “left aligned” means start-aligned where appropriate (`text-align: start`).
- Keep headings closer to the content they introduce than to the preceding block. Encode this with flow spacing, not one-off margins.
- Build scanning with semantic headings, concise paragraphs, genuine lists, and whitespace. Icons may support a list but cannot replace its text or semantics.
- Keep links recognizable without hover. Underlines are the robust default in body copy; if the system uses another treatment, preserve noncolor affordance and visible focus.

## Hierarchy and emphasis

Use size, weight, color, position, spacing, and typeface contrast as coordinated signals. One signal is often enough for emphasis; stacking bold + color + size + italics makes everything compete. Ensure heading levels reflect document structure rather than visual size alone.

Do not ban pure black as a rule. The PDF recommends near-black to soften maximum contrast, but readability depends on the whole palette, font rendering, display, theme, and user needs. Meet the project’s contrast target first; then compare `#000` and a near-black in rendered context.

## Alignment and freshness

- For text-bearing flex/grid rows, test baseline alignment (`align-items: baseline`) against center alignment; choose the one that makes type baselines coherent without misplacing icons or controls.
- Show published and updated dates where freshness affects trust or action. Use semantic `<time datetime="…">`, localized display text, and distinguish publication from meaningful revision.

## Text on images and numbers

- Prefer a stable text surface. When overlay is necessary, use a tested tint, gradient, solid box, blur, or fade that maintains contrast across every responsive crop and image variant.
- Do not hide meaningful image regions behind copy. Define focal-point and fallback behavior.
- Use proportional numerals in prose and `font-variant-numeric: tabular-nums` for columns, timers, changing counters, and aligned financial values when the font supports it.

## Content extremes

Test shortest and longest strings, 200% zoom, narrow width, translated expansion, right-to-left text, mixed scripts, names, unbroken URLs, large numbers, and browser font substitution. Truncate only when task-safe, and provide an accessible way to obtain the full value.

## Verification

Capture computed family, available weight, size, unitless line-height, and measure for representative body, heading, caption, link, control, and tabular-number samples. Render at narrow/wide widths, 100%/200% zoom, longest localization, light/dark themes, and fallback font. Check clipping, overlap, hierarchy, line tracking, focus, and contrast—not screenshots at one viewport only.
