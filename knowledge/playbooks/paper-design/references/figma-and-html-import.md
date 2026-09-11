# Figma, HTML, and clipboard import

Sources: [Paste](https://paper.design/docs/paste),
[Figma](https://paper.design/docs/paste/figma),
[HTML](https://paper.design/docs/paste/html),
[MCP](https://paper.design/docs/mcp), and
[build log](https://paper.design/build-log). Reviewed 2026-09-06.

## Pick a transfer path

| Path | Best use | Work remaining |
|---|---|---|
| Figma selection → copy → Paper paste | Fast editable starting point from actual source | Repair detached bindings and translation losses; verify fidelity |
| Figma MCP → Paper MCP | Targeted semantics, tokens, reconstruction, or clipboard unavailable | Read source dimensions/assets; split deeply nested designs |
| Inline HTML → Paper | Existing code fragment or precise agent composition | Inline resolved styles, provision tokens, verify normalized layers |
| Snapshot → Paper | Real browser-rendered UI as editable reference | Reconcile theme/component owners; test asset fetch and layout |
| SVG/image/text paste | Individual source assets or content | Check editability, sizing, fonts and asset completeness |

A whole-page screenshot is comparison evidence, not an editable implementation.
Clipboard operation requires a human or an actually available desktop capability;
MCP access alone does not prove clipboard automation exists. Do not claim paste
occurred without inspecting the resulting nodes.

## Direct Figma paste

Select the desired content in Figma (Cmd+A can select page content), copy, open the
intended Paper file/page, paste. Start with one representative frame before a whole
library. The result is editable layers, not a linked Figma document.

**Images:** Paper prompts for its Figma extension connection. This is optional for
the paste, but required for images in that flow. The connected account must be able
to open the source file. Rate limits apply; a successful paste can still lack images.
Use the legitimate connection or authorized source asset exports, not an access
workaround. Distinguish this extension from the Figma MCP and browser Snapshot.

### Translation repair map

| Figma feature | Documented paste behavior | Inspect / repair |
|---|---|---|
| Components, instances, variables | Detached; code-connected components unsupported | Recover source identity/overrides; bind Paper tokens; choose component owners separately |
| Slots | Pasted Figma slots added in August 2026 | Check nested content and editability; does not establish linked component instances |
| Masks | Mask and affected nodes hidden | Inventory hidden layers; recover clipping deliberately, not just unhide everything |
| Diamond / rotated radial gradient | Diamond becomes radial; radial rotation dropped | Compare actual source/Paper render before accepting |
| Strokes | Arbitrary dashes, gradient strokes, independent layout-excluded strokes not preserved | Reproduce intent via supported structure or declare difference |
| Noise, texture, repeat, symmetry effects | Not preserved | Use actual authorized assets or a verified alternative; report editability tradeoff |
| Glass | Background blur fallback | Compare result; not equivalent by assertion |
| Drop shadow, layer/background blur | Documented as recreated | Check edges, clipping, opacity and compositing |
| Inner shadow | Reassigned to children with translation logic | Inspect nested surfaces and stacking |
| Rich text | Multiple inline text styles unsupported | Split into editable text nodes where viable; verify wrapping and metrics |
| Truncated text | Height becomes Fit | Test actual long content and parent geometry |
| Pass-through blend | No equivalent background-blend behavior; translated where possible | Verify compositing visually |

June also brought negative gap spacing and Figma import fixes. Retest overlapping
layouts on the installed version before retaining an old manual workaround.

After paste, inspect counts, hidden nodes, assets, text, bounds, and real bindings.
Import/reconcile the theme and repair supported properties with `var(--...)`.
Use `../../pencil/README.md` for exact transfer and its existing manifest gate.

## MCP reconstruction caveats

Official MCP docs warn about SVG fills returned as images, missed instance color
overrides, skipped spacer elements, inset-border intent, code-connected components,
and errors on very large nested trees. Use actual image/SVG exports and smaller
source blocks. Preserve the selected instance's overrides and source render.
For measured grid-to-flex translation, use `../../pencil/references/layout.md`.

Read `index.md` before following the conflicting installed import guide that bans
all variables: current descriptors support provisioned Paper CSS-variable tokens.
Unresolved Figma references still need resolution and mapping; arbitrary source
names are not automatically valid Paper tokens.

## HTML import rules

Only **inline styles** survive ordinary HTML paste. Class names drop and selector
styles are ignored. Do not paste a Tailwind class list or `<style>` block and expect
computed appearance. Use the actual source styles and existing Paper token names.

- `<x-paper-clone node-id="…">` clones a node **in the file**, useful for composing
  existing patterns. A clone is not proof of structural linkage.
- `layer-name` names the layer; `data-paper-locked` locks it; `hidden` hides it.
- `img` and CSS background images are uploaded; public URLs are the documented
  clipboard path. For MCP local assets, follow its current supported asset scheme
  or reachable local URLs. Test from Paper's machine, not just the agent's container.
- All elements use border-box sizing. Inputs become frames with text children,
  not interactive form controls. Hidden/display-none elements remain hidden.
- Blocks containing only inline children flatten to one Text node. Inline nodes
  become inline-block; frame/text styling can introduce wrappers. For independently
  styled labels, use sibling text elements inside a flex frame and verify wrapping.
- Redundant styles can be stripped. MCP writes have additional rules: inspected
  `write_html` guidance favors flex/padding/gap and excludes grid, margin, inline
  layout, and HTML tables. Clipboard capabilities do not override a tool contract.

Prefer targeted insertion/duplication to replacing whole subtrees. Paste on top and
Paste to replace are available in the UI; verify their current menu shortcuts
(`index.md` records a docs conflict). Replacement needs the existing recovery and
confirmation boundary, not an import-specific exemption.
