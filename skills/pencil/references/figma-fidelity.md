# Figma is the spec

Paper copies Figma. It does not reinterpret Figma.

Use this when ripping Atomize (or any Figma file) into Paper, or when the user says stick to Figma / inspo.

## Source of truth

1. Screenshot the Figma node (`get_screenshot` / `save_screenshots`). Keep that image beside the work.
2. `get_node` for that same id: bounds, padding, gap, radius, fill, stroke, effects, type, auto-layout direction.
3. `get_variable_defs` for every bound paint, space, radius, and type style. Create matching Paper tokens. HTML uses `var(--token)`.
4. Artboard width/height = Figma frame width/height. Padding and gap = Figma auto-layout. Do not pick a "cleaner" size.

## What must appear

Copy every column and label the active source shows. The examples below are
from one Atomize snapshot, not required columns, counts, or dimensions for
other files.

- Typefaces: header pill **and** Size + Weights. Left scale names **and** Normal / Medium / Semibold / Bold `Abc` columns. OVERLINE samples are `ABC`.
- Colors: the four boards Figma has (Primary/Secondary/Tertiary, Functional, Gray and Dark, Neutral Black and White). Swatch size 160×168, radius 12, 11 (or 15) stops. Neutral labels follow the Figma text nodes (3, 6, 9, …) even when the bound variable is `Color/black/2`.
- Surfaces / Special Surfaces / Elevations: Figma card count, order, and captions. No extra docs chrome.

If Figma has a specimen column and Paper only has the name column, the copy is wrong.

## Section organizers (Overview-sheets)

If the active source groups boards under organizer frames, preserve those
frames and their measured geometry within the requested scope. Do not invent
an Overview-sheet for a source without one.

Worked Atomize example only (derive all values anew for other sources):

- Each sheet is one rounded card (`#f9f9fa`, radius 64, drop shadow `0 1px 2px -1.5px` + inner `0 -4px 6px`).
- White 1216-wide sidebar on the left: header pill (gradient, radius 1000, "Foundation — {name}" dimmed + section name on a white sub-pill), heading (88px display), description (32px, line-height 40, letter-spacing −0.5), footer pills (atomizedesign.com + version).
- Content boards live inside the sheet at x = 1408 (1216 sidebar + 192 gap), y per Figma positions.
- Description highlights: keep highlighted list lines (palette names, Typeface 1/2) as dark `#0a0c11` spans; body stays the muted gray. A section that is a single color stays a single color.

## Compare before the next artboard

`paper_get_screenshot` of the artboard vs the Figma screenshot.

Fix when any of these differ: missing column, wrong label, wrong fill, packed intrinsic widths where Figma uses a grid cell, white-on-white text, a backdrop Figma does not use.

Do not move on because it is "close enough."

## Tokens vs paint

Bound Figma variables become Paper tokens (same path, kebab, `--` prefix). Unbound Figma paint stays a raw value only for that property.

Do not flatten `Color/brand/500` to a one-off hex in HTML. Do not mint `--color-primary` when Figma already named the variable.

Paper cannot switch Figma modes (Accent-2, Typeface-2, Dark) on one node. Document extra modes as extra boards, still bound to tokens created from those mode values.

## Fonts

`get_basic_info.fontFamilies` is the allow-list. If Figma's family is missing, report the constraint; use a fallback only with user acceptance, and do not claim pixel-perfect fidelity. Do not add a caption in the design that Figma does not have.

## Inspo

For an accessible Figma file, use the source-node and variable workflow above.

For a captured visual reference without Figma nodes:

1. Use the original captured image as the render specification. Record its
   dimensions, scale, crop, and requested scope; do not invent a Figma file or
   call `get_node` or `get_variable_defs` for an image-only source.
2. Measure visible bounds, spacing, colors, and text from the capture. Label
   inferred structure and uncertain font/geometry measurements. Figma variables,
   semantic bindings, hidden states, and original node metrics are **unavailable**,
   not absent or verified. Do not fabricate their names or values.
3. Build editable Paper layers from that evidence. Reuse matching project tokens
   when verified; distinguish measured paint from recovered source variables.
   Use supplied assets where available rather than flattening the whole capture
   into the deliverable. Report assets or detail that cannot be recovered.
4. Capture a fresh Paper render at the same scale/crop and compare it with the
   reference. Verify visible likeness; do not claim recovered source structure,
   variable fidelity, or unknown states. Report remaining uncertainty explicitly.

Neither route authorizes restyling the source into a Paper-default kit.
