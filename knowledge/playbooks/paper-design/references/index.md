# Official source map

Reviewed 2026-09-27. All **nine** `/docs` pages in the official sitemap were fetched
and read from the live origin, including the hub. The hub and `llms.txt` were also
checked for additional docs links; none were missing from this set. This is a
curated working reference, not a verbatim mirror. Tutorial videos were linked by
the docs but not reviewed.

| Official page | Coverage here |
|---|---|
| [Docs hub](https://paper.design/docs) | This inventory and skill routing |
| [Tokens and themes](https://paper.design/docs/tokens) | `themes-and-tokens.md`: types, create/use/detach/update/copy/delete, code ownership, roadmap |
| [Paste overview](https://paper.design/docs/paste) | `figma-and-html-import.md`: supported inputs and replace/on-top caution |
| [Paste from Figma](https://paper.design/docs/paste/figma) | `figma-and-html-import.md`: clipboard, image authorization, all translation categories |
| [Paste from HTML](https://paper.design/docs/paste/html) | `figma-and-html-import.md`: inline styles, assets, custom elements/attributes, text and frame normalization |
| [Vector editing](https://paper.design/docs/svg) | `canvas-and-support.md`: import/generation/editing, paths, snapping, roadmap |
| [MCP server](https://paper.design/docs/mcp) | `mcp-and-handoff.md`: CLI/plugin setup, legacy HTTP, operations, Figma/content/code workflows, recovery |
| [Support](https://paper.design/docs/support) | `canvas-and-support.md`: shortcut families, file/network/protocol/WSL troubleshooting |
| [Snapshot local images](https://paper.design/docs/support/snapshot-local-images) | `canvas-and-support.md`: framework-specific CORS routes and local-asset caveats |

## Discovery and release sources

- [Machine-readable site index](https://paper.design/llms.txt) and
  [sitemap](https://paper.design/sitemap.xml): rediscover the docs set, not just known URLs.
- [Build log](https://paper.design/build-log): historical April–August 2026 entries
  reviewed on 2026-09-06. Not re-audited for this docs refresh; retained release
  claims are historical announcements, not a current feature inventory.
- [Snapshot quick start](https://paper.design/snapshot-extension): browser capture
  workflow, checked against the live origin on 2026-09-27.

## Evidence and conflicts

Relevant installed descriptors were inspected on 2026-09-27: file/page context,
token listing/creation/updates, node search, HTML writes, and style updates. The
read-only `paper-mcp-instructions` guide and relevant `figma-import` passages were
retrieved. No canvas was inspected or modified; no connection migration, clipboard
transfer, token propagation, or new runtime feature was tested.

- **Cached pages lag the origin.** The web extractor returned token docs saying
  creation/updates were MCP-only and setup docs centered on HTTP. Direct origin
  reads documented Theme-tab editing and the newer CLI/plugin setup. Recheck the
  live page before treating a removed capability as a regression.
- **Setup changed, HTTP still works.** Current docs prefer `paper mcp` stdio or host
  plugins/extensions. The older localhost endpoint remains supported. Tool
  discovery can work while Desktop is closed; canvas reads/writes still require it.
- **Schemas can exceed the docs.** Token descriptors include opacity; `find_nodes`
  searches all pages by default. Read installed schemas rather than assuming the
  website's category list or an older page-scoped search contract is exhaustive.
- Token docs list native multiple modes and bundled theme classes as **roadmap**.
  Do not reinterpret the Theme tab as a working light/dark mode system.
- The Figma paste introduction says variables are unavailable, while token docs
  and tools support Paper tokens. The specific import limitation is that **Figma
  variables detach on paste**, not that Paper lacks tokens.
- Installed `figma-import` guidance still says all `var(...)` must become literals.
  Current token docs and `write_html` / `update_styles` descriptors support design
  tokens. Resolve the source value, provision the destination token, and verify its
  binding rather than flattening every reference. Probe an approved disposable
  fixture if the install disagrees.
- That guide also suggests shortening instance-path IDs. Preserve override context:
  follow the actual Figma tool's accepted ID form and verify the selected instance,
  not just its master. The docs' read-only Figma example is not proof that every
  installed Figma integration is read-only; inspect permissions before granting them.
- The paste overview omits Shift in some shortcuts; support lists **Shift+Cmd+V**
  for Paste on top and **Shift+Cmd+R** for Paste to replace. The visible app menu
  wins when shortcuts conflict; Cmd+R alone is also documented as Rename.
- General MCP/support prose still describes the open file. Installed guidance and
  schemas support explicit file/page targets, including background pages. Confirm
  scope instead of assuming the visible tab is always the mutation target.

Refresh the nearest source and test the specific operation rather than treating
an old limitation, a guide's aesthetic preference, or marketing language as a
universal contract. Existing assets, brand choices, and task scope remain owners;
provider guidance is not permission to invent a new design system.
