---
name: pencil
description: "Use when copying Figma or inspo into Paper, ripping a Figma file onto a Paper canvas, setting Paper tokens from Figma, or when the user says pencil, paper skill, stick to Figma, or figma-to-paper. Copies Figma literally: screenshot is the spec, variables to the bone, every Figma column (including type specimens), one Paper page per Figma page. Never invent a simplified showcase."
---

# Pencil

## Core Principle

Figma is the spec. Paper tokens are the one settings set. Screenshot the Figma node, copy its bounds and every column it shows, bind paints to `var(--token)`. Do not invent a simpler layout. Spread the file: one Paper page per Figma page, one artboard per component set.

## When to Use / NOT

- **Use when:** the user wants a Figma frame, component set, or template copied into Paper; wants Paper to stick to Figma or inspo; wants Paper tokens from Figma; says pencil, paper skill, stick to Figma, or figma-to-paper.
- **NOT when:** the source is a live website (`web-reference`); the job is app code from Figma; Paper work has no Figma source (design in Paper directly).

## Workflow

1. Probe MCP (`references/mcp.md`). Paper Desktop must have the target file open. Prefer Figma screenshot + `get_node`. Official Figma `get_design_context` if authorized. Do not parse MCP dumps with scripts as a stand-in for looking at the frame.
2. Screenshot the Figma node. Keep that image beside the Paper work.
3. **HARD-GATE: variables to the bone, then HTML.** `get_variable_defs` first (`references/tokens.md`). Every Figma variable used by the frame becomes a Paper token (path, alias, resolved value). Bound fills/spacing/type use `var(--that-token)`. Raw hex or px only when Figma has no variable on that property. Neutral colors first, then primary. Spacing and radius smallest first. A Figma paste into Paper detaches components and variables ([paste/figma](https://paper.design/docs/paste/figma)); paste is not a substitute for this step.
4. **HARD-GATE: spread the file** (`references/organization.md`). `create_page` for each Figma page you are ripping. One artboard per Figma component set or top-level frame. 80px between artboards. Recreate any Figma `Overview-sheet` section organizers (white sidebar + section card) and group the boards inside them at x = 1408 — do not leave boards floating on the page. Cover stays on Cover; Buttons do not land on Cover.
5. Size each artboard from that Figma frame: bounds, padding, gap, radius, fill, dashed stroke. Paper forbids `display:grid`. Emulate a Figma GRID with flex rows whose **cells** are the max sibling width in that column (`references/layout.md`).
6. Copy one variant from `get_node`: fills, padding, radius, type, gap. Export IMAGE fills and VECTOR icons with Figma screenshot tools onto disk, then `paper-asset://`. Do not draw a substitute for an image fill.
7. `write_html` one visual row, inline styles only ([paste/html](https://paper.design/docs/paste/html)). Repeat with `duplicate_nodes`, `update_styles`, or `<x-paper-clone>`. Primary and Secondary stay separate text nodes (Paper has no rich text). Break large Figma trees into parts ([mcp](https://paper.design/docs/mcp)).
8. **HARD-GATE: screenshot compare** (`references/figma-fidelity.md`). Paper `get_screenshot` of the artboard vs the Figma screenshot. Missing columns (type specimens), wrong labels, or a backdrop Figma does not use means the copy is not done. Fix before the next artboard.
9. **Stop** when the requested Figma frames match, or the user redirects. Do not start the next Figma page on the same Paper page.

## Red Flags

- Inventing a showcase, dropping Figma specimen columns, or demo labels Figma does not use.
- Skipping tokens, flattening a bound Figma variable to a hex in HTML, or minting `--color-primary` when Figma already named the variable.
- Flex-packing buttons with only `gap` between intrinsic widths when Figma uses a GRID whose cell is the largest size (xl).
- Python (or other scripts) walking node JSON instead of a screenshot + targeted `get_node`.
- A footer that documents a font fallback as if it were the design. If Paper lacks the Figma family, use an installed font and say so; do not decorate it.
- Putting Cover, Tip, Button, Icon-button, success, and danger on one Paper page or one artboard.
- Leaving content boards floating without their Figma Overview-sheet section organizer (sidebar, "Foundation —" pill, heading, description, footer).
- Treating Figma paste as a full import: Paper detaches components and variables; masks hide; code-connected components do not convert.

## Verification

- `get_basic_info` lists Paper tokens that match Figma variable paths (kebab, `--` prefix). Bound styles in HTML are `var(--token)`, not baked hex.
- Paper screenshot vs Figma screenshot: same labels, fills, column count (Typeface Normal/Medium/Semibold/Bold `Abc`), and column rhythm.
- Each state column width equals the Figma max size in that set (Button xl = 297px), gap equals Figma `autoLayout.gap`.
- `list_files` / `get_basic_info`: component work lives on a page named after the Figma page; each component set is its own artboard.

## References

- `references/layout.md`: Figma GRID to Paper flex cells; why gap-24 on 217px buttons looks tight
- `references/tokens.md`: `create_tokens` order and a starter Button set
- `references/mcp.md`: Paper and Figma tool probe, asset export, timeout rules
- `references/organization.md`: Paper pages vs artboards; do not dump a Figma file onto one page
- `references/official.md`: paper.design/docs limits (paste, tokens, MCP, SVG, HTML)
- `references/figma-fidelity.md`: screenshot is the spec; Typefaces/Colors/Surfaces must include every Figma column
