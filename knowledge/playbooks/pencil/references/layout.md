# Figma GRID to Paper cells

Paper `write_html` rejects `display:grid`. A Figma `COMPONENT_SET` with `autoLayout.direction: GRID` still has a cell size. Copy that cell, not only the gap.

## Worked example: the spacing miss

The following values belong to one source snapshot, not a Button size policy.
For each active source, measure its actual column tracks, variant bounds,
alignment, gap, and padding. A track need not equal the largest variant.

Atomize **Button** (`8003:300`):

- artboard padding 40, gap 24, radius 40, fill `#ffffff`, dashed 1px `rgba(0,0,0,0.12)`
- four state columns
- five size rows per type (xs 24 / sm 32 / md 40 / lg 48 / xl 56 tall)
- xl width **297px** is the column track
- md button width is **217px**

A flex row with `gap: 24px` between 217px buttons puts 24px of air between chromes. Figma puts each button in a 297px track, so md-to-md gutter is `(297 - 217) + 24 = 104px`. That is the "not enough spacing" screenshot: the gap token was right, the cell was missing.

## Example translation

Each state is a **cell**, then the button inside it:

```html
<div layer-name="primary md" style="display:flex; align-items:center; gap:var(--space-gap-set);">
  <div layer-name="cell default" style="display:flex; align-items:center; width:var(--button-col); height:40px;">
    <div layer-name="primary / md / default" style="display:flex; align-items:center; width:217px; height:40px; /* Figma padding/radius/fill */">
      ...
    </div>
  </div>
  <!-- hover, pressed, disabled cells, same --button-col -->
</div>
```

- In this example, `--button-col` is the measured track, equal to the xl width. Derive it from the active grid, not a global maximum-width rule.
- `--space-gap-set` = Figma GRID gap (24px).
- Align the button to the start of the cell (`align-items:center` vertically, default horizontal start).
- Do not stretch the button to 297px; that changes the chrome.

Paper MCP `write_html` forbids `display:grid` and `margin`. Official paste from Figma can keep more CSS, but agent writes still follow the MCP HTML rules. Figma MCP also drops spacer frames ([docs/mcp](https://paper.design/docs/mcp)); never trust MCP layout without the screenshot.

## Checklist before writing the next row

1. Figma screenshot of that row in view.
2. Cell width equals the measured source track; it need not equal the largest variant.
3. Button width equals that variant's bounds, not the cell.
4. Gap and artboard padding come from tokens, not a new number.
