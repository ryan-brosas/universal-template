# Official source map

Reviewed 2026-09-06. All **nine** `/docs` pages in the official sitemap were fetched
and read, including the hub. The documentation hub and `llms.txt` were also checked
for additional docs links; none were missing from this set. This is a curated
working reference, not a verbatim mirror. Re-fetch the relevant source when behavior
or versions differ. Tutorial videos were linked by the docs but not reviewed.

| Official page | Coverage here |
|---|---|
| [Docs hub](https://paper.design/docs) | This inventory and skill routing |
| [Tokens and themes](https://paper.design/docs/tokens) | `themes-and-tokens.md`: types, create/use/detach/update/copy/delete, code ownership, roadmap |
| [Paste overview](https://paper.design/docs/paste) | `figma-and-html-import.md`: supported inputs and replace/on-top caution |
| [Paste from Figma](https://paper.design/docs/paste/figma) | `figma-and-html-import.md`: clipboard, image authorization, all translation categories |
| [Paste from HTML](https://paper.design/docs/paste/html) | `figma-and-html-import.md`: inline styles, assets, custom elements/attributes, text and frame normalization |
| [Vector editing](https://paper.design/docs/svg) | `canvas-and-support.md`: import/generation/editing, paths, snapping, roadmap |
| [MCP server](https://paper.design/docs/mcp) | `mcp-and-handoff.md`: host setup routes, operations, Figma/content/code workflows, recovery |
| [Support](https://paper.design/docs/support) | `canvas-and-support.md`: shortcut families, file/network/protocol/WSL troubleshooting |
| [Snapshot local images](https://paper.design/docs/support/snapshot-local-images) | `canvas-and-support.md`: framework-specific CORS routes and local-asset caveats |

## Discovery and release sources

- [Machine-readable site index](https://paper.design/llms.txt) and
  [sitemap](https://paper.design/sitemap.xml): rediscover the docs set, not just known URLs.
- [Build log](https://paper.design/build-log): April–August 2026 entries reviewed
  for workflow changes; older entries were searched, not exhaustively summarized.
- [Snapshot quick start](https://paper.design/snapshot-extension): browser capture workflow.

## Additional inspected evidence and conflicts

The installed Paper MCP descriptors were inspected for token creation, updates,
listing/export formats, node search, HTML writes, and style updates. No Paper
canvas was modified and no clipboard transfer or token-propagation experiment was
run while authoring this skill. Schema inspection is not runtime validation.

- Token docs list native multiple modes and bundled theme classes as **roadmap**.
  Do not reinterpret the Theme tab as a working light/dark mode system.
- The Figma paste page's introduction says variables are unavailable, while the
  token docs and installed token tools support Paper tokens. Interpret the specific
  import statement: **Figma variables detach on paste**, not “Paper has no tokens.”
- Installed `get_guide` topic `figma-import` says all `var(...)` must be replaced
  with literals. Current token docs and inspected `write_html` / `update_styles`
  descriptors explicitly support design-token CSS variables. Resolve the source
  value for evidence, create the destination token, and verify its binding instead
  of globally flattening tokens. Probe a disposable fixture if the install disagrees.
- That guide also suggests shortening instance-path IDs. Do not discard instance
  override context blindly: follow the actual Figma tool's accepted ID form and
  verify that returned data belongs to the selected instance, not just its master.
- The paste overview omits Shift in some shortcuts; support lists **Shift+Cmd+V**
  for Paste on top and **Shift+Cmd+R** for Paste to replace. Prefer the visible app
  menu when shortcuts conflict; Cmd+R alone is also documented as Rename.
- August release notes add background-tab multi-file agent work. Older MCP prose
  describes only the open file. Use explicit `fileId` where supported and verify
  page context; never rely on “the visible tab must be the target.”

These qualifications are intentional. Refresh the nearest source and test the
specific operation rather than treating either an old limitation or marketing
language as a universal contract.
