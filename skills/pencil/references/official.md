# Paper docs (official)

Source: [paper.design/docs](https://paper.design/docs). Prefer these over guessing Paper behavior.

## MCP

[docs/mcp](https://paper.design/docs/mcp)

- Paper Desktop starts MCP when a file is open. The open file is the context.
- Stale long sessions are the usual failure. Restart the agent session. Toggle MCP off/on if the host still lists tools the agent cannot call.
- Sync tokens from Figma: both MCPs in the same host; Figma file and Paper file both open; **select a Figma element that has the variable or style assigned**.
- Split large nested Figma designs. Figma MCP often: SVG fills as images, ignores spacer frames, misses inset-border intent, fails on code-connected components.

## Tokens

[docs/tokens](https://paper.design/docs/tokens)

- Tokens are CSS variables. Update one, update every use.
- Types today: color, radius, spacing, container, breakpoint, font family, font weight, font size, line height, letter spacing.
- Not yet: theme classes (H1 bundles), multiple theme modes (dark/compact).
- Per file. Paste into another file does not stay linked.
- Detach keeps the current value and drops the link. Pencil should not detach while copying a system.

## Paste from Figma

[docs/paste/figma](https://paper.design/docs/paste/figma)

- Copy in Figma, paste in Paper: editable layers. Optional Figma extension for images (rate limits apply).
- **Components, instances, and variables detach on paste.** Code-connected components are not supported.
- Masks and affected nodes hide. Diamond gradients become radial. No gradient strokes, no arbitrary dash lengths. Glass becomes background blur. Noise/texture/repeat not preserved. Inner shadows land on children (CSS).
- No rich text: one text node, one style. Truncation height becomes fit-content.
- Pass-through blend has no CSS equivalent.

Use paste for a fast visual dump if the user wants it. Still run variables-to-the-bone via MCP so names survive.

## Paste from HTML

[docs/paste/html](https://paper.design/docs/paste/html)

- Inline styles only. Classes drop.
- `<x-paper-clone node-id="...">` clones by id.
- `layer-name`, `data-paper-locked`, `hidden`.
- `box-sizing: border-box` everywhere.
- A block with only inline children flattens to one text node. Keep Primary and Secondary as sibling text nodes in a flex frame.
- Public image URLs (or `paper-asset://` / localhost the machine can fetch).

## SVG

[docs/svg](https://paper.design/docs/svg)

- Paste SVG as editable vectors. Do not AI-generate an SVG (`Ctrl⇧J`) unless the user asked.
- Export Figma VECTOR icons as SVG and `paper-asset://` them. Do not replace IMAGE fills with hand-drawn SVG.

## Support

[docs/support](https://paper.design/docs/support)

- Wrong file: `get_basic_info`.
- WSL: mirrored networking for `127.0.0.1` MCP.
- Local snapshot images need CORS for `https://app.paper.design`.
