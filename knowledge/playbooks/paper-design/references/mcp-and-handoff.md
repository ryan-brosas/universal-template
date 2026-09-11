# MCP connection and design/code handoff

Source: [Paper MCP](https://paper.design/docs/mcp), reviewed 2026-09-06.
Use live tool discovery for exact arguments; this is an operation map, not a schema
cache. Read the installed `paper-mcp-instructions` guide when available.

## Connection

Paper Desktop starts its local MCP server when a file is open. The documented
Streamable HTTP endpoint is `http://127.0.0.1:29979/mcp`. Prefer the host's existing
Paper connection rather than installing a duplicate. “Localhost” must reach the
machine running Paper; it is not inherently the same machine as a remote agent.

The official page supplies these host-specific setup routes:

| Host | Route |
|---|---|
| Cursor | `/add-plugin paper-desktop` or Paper in Cursor Marketplace; inspect Tools & MCP |
| Claude Code CLI | Marketplace `paper-design/agent-plugins`, plugin `paper-desktop@paper`; manual HTTP registration also documented |
| Claude Desktop Code tab | Customize → Add plugin → Add marketplace; use the same marketplace/plugin |
| Claude Desktop manual config | `mcpServers` entry invoking `npx mcp-remote` with the local endpoint; restart |
| Codex | Settings → MCP Servers → custom Streamable HTTP server |
| VS Code Copilot | `.vscode/mcp.json`, `servers.paper`, HTTP type and endpoint |
| Antigravity | Manage MCP Servers → raw config; `mcpServers.paper.serverUrl` |
| OpenCode | `opencode.json`, `mcp.paper`, remote type, URL, enabled |

Fetch the live setup section before editing host configuration. Do not translate
one host's JSON shape mechanically into another. No credentials should be copied
into a skill. Configuration changes follow the host's ordinary approval boundary.

Confirm discovery and use `get_basic_info` to inspect file/page/artboards. The docs'
red-rectangle test is a **write**: run it only in an approved disposable canvas.
Multi-file/background-tab support means explicit `fileId` is safer than relying on
the frontmost tab; verify page context after switching. Tool visibility alone is not
proof the intended file or asset path is accessible.

## Operation map

| Need | Documented tools / approach |
|---|---|
| Orient | `get_basic_info`, `get_selection` |
| Inspect bounded structure | `get_node_info`, `get_children`, `get_tree_summary` |
| Inspect appearance | `get_computed_styles`, `get_screenshot`, `get_fill_image` |
| Inspect fonts | `get_font_family_info`; follow with a rendered text specimen |
| Read code | `get_jsx`, Tailwind or inline-styles format |
| Read workflow guidance | `get_guide`, including `figma-import`; note conflicts in `index.md` |
| Build | `create_artboard`, incremental `write_html` |
| Reuse / rearrange | `duplicate_nodes` returns descendant mapping; `move_nodes` preserves IDs |
| Repair | Batched `set_text_content`, `rename_nodes`, `update_styles` |
| Remove | `delete_nodes`; preserve originals until replacement is verified |
| Export | `export`: per-node formats/scales or nodes already marked for export |
| Finish | `finish_working_on_nodes` releases working indicators |
| Tokens | See `themes-and-tokens.md`; newer installed tools exceed the website's tool list |

Bound reads to relevant blocks. Batch independent style/text operations where
supported, but respect dependencies: destination context and tokens before binding,
parents before children, duplicate mappings before substitutions. Inspect individual
results and read back after ambiguous failure before repeating a mutation. The
component workflow owns recovery and synchronization; do not create a competing one.

## Three documented workflows

**Figma system → Paper:** both MCPs in one host, correct files, source element with
assigned variable/style selected. Inspect full relevant source semantics, then
create tokens and editable usages. A sticker sheet alone does not verify bindings.
See `figma-and-html-import.md` for translation limits and source-instance pitfalls.

**Real content → Paper:** connect an authorized source such as Notion; select the
specific destination section. Replace placeholders with real content. Test long
names, optional fields, and translations against existing component fitting rules.
Content access does not authorize unrequested edits to the upstream data source.

**Paper → application:** inspect the selected frame's structure, tokens, assets,
and relevant viewport variants. Flex layouts and containers make intent easier to
translate. Implement one bounded section in the existing project stack; preserve
component and token owners instead of generating a parallel app. Use the repository's
actual commands for preview/testing. A local dev URL is not a deployed website.

Validate responsive behavior using actual narrow/wide layouts and intermediate
widths, not just the existence of breakpoint tokens. Check semantics, keyboard
behavior, accessibility, and interactions in code; Paper input frames do not supply
them. Snapshot can bring the rendered implementation back as editable comparison
material, but is not lossless component or theme round-trip synchronization.

## Recovery

Wrong document: read identity before more writes. Connected-but-missing tools:
rediscover current schemas; a stale agent session may need restart or MCP toggle.
If the host itself cached the old server, restart it. Updated Pro limits may require
updating/restarting Paper Desktop. WSL may need mirrored networking; see
`canvas-and-support.md`. Do not repeatedly retry a dead screenshot session or
restart another person's applications automatically.
