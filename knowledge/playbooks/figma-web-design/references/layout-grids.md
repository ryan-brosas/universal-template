# Layout grids and content widths

Course examples, not required project values. Reuse the approved source grid and
its bindings. Use these examples only when creating a new layout system has been
authorized; rem conversions below assume a 16 px root.

## Artboard and content widths

| Layout | Artboard width | Content (container) width | Desktop margin |
| --- | --- | --- | --- |
| Wide | 1600 px / 100 rem | 1360 px / 85 rem | 120 px |
| Default | 1440 px / 90 rem | 1280 px / 80 rem | 80 px |
| Narrow (legacy) | 1360 px / 85 rem | 1140 px | 110 px |

The course uses 1440/1280 as its default, not a device-coverage standard. Choose
viewports from the project's requirements. For a centered container, derive
each margin as `(artboard width - content width) / 2`, then verify alignment
against the source grid without modifying its tokens to hide a mismatch.

## Grid recipe

- **Desktop:** 12 columns, gutter 20-24 px, margin matched to the content width above. Save a rows grid at 20 px row height and low opacity as an alignment aid.
- **Tablet** (e.g. iPad Pro 11): 6 columns, margin 60-80 px, gutter 20 px.
- **Mobile** (e.g. iPhone 16): 2 columns, margin 20 px, gutter 20 px. 20-24 px is the usable band; less crowds the edge, more wastes phone width.

Save each combination as a named layout-grid style so every new frame applies it in one action.

## Inner container widths

A section often needs a narrower column than the page container.

Rounded course examples; derive exact spans from the selected gutter and columns.

| Layout | Default container | Medium container | Small container |
| --- | --- | --- | --- |
| 1440 px artboard | 1280 px | 848 px | 630 px |
| 1600 px artboard | 1360 px | 898 px | 668 px |

For `n` columns, container width `W`, gutter `g`, and a span of `k` columns:
`column = (W - (n - 1) * g) / n`; `span = k * column + (k - 1) * g`.
Verify against guides; rounded examples above are not exact at every gutter.

## Measuring and verifying

- Set up the artboard and guides once per project; reuse the same starting artboard from the design system rather than rebuilding it.
- Keep guides visible while building and toggle the layout grid off once alignment is established; switch the grid on to verify a finished section.
- Inspect edges at pixel zoom, but distinguish unintended drift from legitimate
  fractional column widths. Odd or fractional values alone are not defects.
- There is no global style for rulers; keep a saved "layout starter" frame in the design system and copy it into new pages.
