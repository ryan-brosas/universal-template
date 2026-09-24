# Elements, styles, and layout setup

Reference mechanics for approved asset adjustments or explicitly authorized new
assets. Reuse linked components first; these recipes do not authorize replacing
them with primitives. Preserve source bindings and editable originals.

## Frames versus groups

- **Frames** are containers: they support auto layout, explicit sizing, constraints, and clipping. Use them for sections, cards, buttons, and banners. Name every one.
- **Groups** are light wrappers. They do not take auto layout; use them to bundle compound graphics for a single export or to keep layers tidy.
- Use the source button instance. If a new button is explicitly authorized, use
  auto layout rather than a rectangle/text/group assembly.
- Keep layer icons legible as you build: frame, auto-layout frame, group, and component each look different in the layer tree.

## Setting up a screen

1. Create the frame and name it for its page.
2. Apply the saved layout-grid style instead of adding grids by hand.
3. Paste the reusable "layout starter" frame (grid plus guides) from the design system rather than rebuilding guides.
4. Build with the layout grid off and the guides on; switch the grid on to verify a finished section.
5. Use the source spacing tokens and grid rhythm; do not substitute the course's
   example gaps for the project's values.

## Positioning and responsiveness

- Alignment aligns an element to its outer frame or group.
- With several elements selected, the gap field sets spacing; a single selection does not show it.
- Sizing can be auto width, auto height, fixed, or aspect-locked.
- Constraints control children in regular frames. Within auto layout, normal
  children use auto-layout sizing; constraints apply to children that ignore its
  flow. See the [auto-layout guide](https://help.figma.com/hc/en-us/articles/360040451373-Guide-to-auto-layout).

## Shapes, vectors, and SVG

- Shapes are vectors: corner-radius handles on canvas, stroke aligned inside/centre/outside, dashed strokes, and the pen tool for custom paths.
- The arrow tool makes arrows and simple icons with independent front and back strokes, removing reliance on an icon font.
- Star and polygon expose point count and ratio, which is enough to build badges quickly.
- **Outline stroke** converts a stroke to filled geometry. On an authorized
  export copy, use it when the export requires outlines; keep the editable
  original and do not flatten linked source assets.
- **Union** a multi-vector mark before exporting: the exported SVG then reads as one shape, and effects such as gradients apply across the whole mark instead of per sub-vector. Mask, subtract, intersect, and exclude cover the remaining compound-graphic cases.
- **Masking:** select the shape and the image, then mask. The shape defines the crop and stays editable afterwards, so a custom or unioned shape can produce non-rectangular graphics.
- Prefer SVG for vector icons and marks. Verify gradients in the actual target
  renderer; do not silently remove visual content or substitute raster output.

## Images

- Drag an image onto the canvas, or set it as a frame fill so it behaves like a cover background.
- Dragging a new image onto an existing fill swaps it, which makes comparison fast.
- Double-click an image for fill (cover), fit, crop, and exposure adjustments.

## Export

- Export at 2x-3x. JPEG for photography, SVG for icons and marks, PNG only when transparency or a gradient requires it.
- Check the export preview before writing the file; a wrong selection exports the wrong frame.
- Export a whole screen frame as PDF for client review and handoff.
- `.fig` local copy exports the file for transfer, and a `.fig` dragged into the workspace imports it.

## Typography

- Figma font sizes use pixels; line height and letter spacing also support
  percentages. Map values to implementation units during handoff.
- Set line height explicitly rather than leaving it on auto: roughly 100 percent for tight display titles and 150-175 percent for body text.
- Letter spacing takes pixels or percentages; the scrubber is faster than typing.
- Check support in the target browser/runtime before relying on advanced text
  features; do not assume they are either universally available or impossible.
- Use paragraph spacing inside one text object instead of many stacked text layers.
- Save global text styles for type roles and bind font size, line height, and letter spacing to variables where the tool allows.
- Keep a spell-check plugin installed while working with text.

## Colour

- A fill can be solid, a gradient with multiple stops (linear, radial, angular, diamond), an image, or video.
- Two opacity levels exist: paint-level opacity affects only that fill or stroke, while element opacity affects the whole element including strokes.
- Prefer colour variables over one-off styles so values stay changeable across the system, and keep hex values available for transfer to CSS.
- The built-in contrast checker reports pass/fail per text role as a guide; formal conformance belongs to [wcag-accessibility-practices](../../wcag-accessibility-practices/README.md).

## Borders and effects

- Corner radius can be set per corner, and radius should be bound to a variable so every card, input, and button matches.
- A drop shadow maps directly to a CSS box-shadow: horizontal, vertical, blur, and spread. Record the metrics so the built site reproduces the design.
- Inner shadow produces neomorphic surfaces; layer blur blurs an element; background blur produces the glassmorphism effect and needs a fill opacity above zero.
- Save effect styles and reuse them. Inconsistent shadows across a site read as amateur.
