# MCP connection and design/code handoff

Source: [Paper MCP](https://paper.design/docs/mcp), checked at the live origin on
2026-09-27, plus relevant installed schemas and guidance. Use live discovery for
exact arguments; this is an operation map, not a schema cache. Read the installed
`paper-mcp-instructions` guide when available, within the task's asset/scope rules.

## Connect through the current setup

Opening Paper Desktop installs its CLI. For a new connection, use **Connect your
agent** in the editor or MCP panel (deselect nodes if the panel is hidden). The
current default is a host plugin/extension or **stdio via `paper mcp`**, not a new
localhost-HTTP entry. Reuse a working connection instead of installing a duplicate.

| Host | Current documented route |
|---|---|
| Cursor | Marketplace plugin or `/add-plugin paper-desktop`; inspect Tools & MCP |
| Claude Chat | Add to Claude installs the `.mcpb` extension; restart Claude |
| Claude Code / Claude Code tab | Plugin `paper-desktop@paper` from marketplace `paper-design/agent-plugins` |
| GitHub Copilot app | Add to GitHub Copilot; manual command is the Paper CLI path with argument `mcp` |
| VS Code | Add to VS Code, then start the server; manual workspace config uses `servers.paper`, type `stdio`, CLI command and `args: ["mcp"]` |
| OpenCode | Local MCP with command array `["/path/to/paper", "mcp"]`; restart OpenCode |
| ChatGPT / Codex CLI | Share Codex config; add once. ChatGPT uses a new Work-tab chat; manual CLI registration is `codex mcp add paper -- /path/to/paper mcp` |
| Antigravity | CLI command plus `mcp` argument in MCP config; restart; applies to its products |
| Other agents | Copy the Paper CLI path from the MCP panel; register that executable with argument `mcp` as stdio using the host's own config shape |

`/path/to/paper` is a placeholder: use the actual path from the MCP panel. Fetch the
live host-specific instructions before editing configuration; one host's JSON
shape is not portable. The CLI can expose tools/instructions while Desktop is
closed, but **canvas reads and writes still need Desktop and the intended file**.
Tool discovery alone is not a successful canvas connection test.

### Existing HTTP setups

Desktop still serves Streamable HTTP at `http://127.0.0.1:29979/mcp` while a file is
open. Existing HTTP and `mcp-remote` setups can continue working. Localhost must
reach the Paper machine, not an unrelated remote agent/container. Current
Cursor/Claude plugins already use the CLI; the docs say they need no manual
migration. Inspect the installed version before diagnosing it.

For an authorized migration, preserve the old config, identify the single old
entry, replace it with the host's current setup, then rediscover and read context.
Do not leave duplicate HTTP and stdio registrations. This guide does not authorize
changing host config, restarting applications, or upgrading them unattended.

## Establish file and page context

After discovery, use `get_basic_info` to confirm file, pages, artboards, fonts, and
tokens. Carry explicit `fileId` and, for page-scoped calls, `pageId`: the user can
change the active page between calls. Node-targeted operations follow that node's
page. `open_file` does not switch pages for an already-open file; it is not a way
to force the user's view to your target page.

Inactive-page geometry may be `null` when layout has not been measured. Do not
convert missing measurements into zero or invent bounds. Check returned file
identity throughout the task. Token-header `contentHash` changes mean cached
token context is stale; refresh before relying on it.

The docs' Hello World, swatch, and generated-image connection examples are writes,
not read-only probes. Test creation only in an approved disposable canvas; image
generation also requires explicit permission and consumes usage.

## Operation map

Discover the installed operation before using these names; availability and
argument requirements can vary by version.

| Need | Tools / approach |
|---|---|
| Orient | `get_basic_info`, `get_selection` |
| Inspect bounded structure | `get_node_info`, `get_children`, `get_tree_summary` |
| Inspect appearance | `get_computed_styles`, `get_screenshot`, `get_fill_image` |
| Inspect fonts | `get_font_family_info`; follow with a rendered text specimen |
| Read code | `get_jsx`, Tailwind or inline-styles format |
| Read workflow guidance | `get_guide`; resolve known import conflicts using `index.md` |
| Build | `create_artboard`, incremental `write_html` |
| Reuse / rearrange | `duplicate_nodes` returns descendant mapping; `move_nodes` preserves IDs |
| Repair | Batched `set_text_content`, `rename_nodes`, `update_styles` |
| Remove | `delete_nodes`; preserve originals until replacement is verified |
| Export | `export`: inspect current formats, scales, page scope and configured exports |
| Finish | `finish_working_on_nodes` releases working indicators |
| Tokens / consumer search | See `themes-and-tokens.md` |

Bound reads to relevant blocks. Prefer cloning existing patterns over rewriting
HTML; make authorized new HTML incrementally in small visual groups. Batch
independent style/text updates where supported, but respect dependencies: context
and tokens before binding, parents before children, clone mappings before content
substitution. Check per-entry results and `ignoredStyles`; inspect ambiguous
failures before retrying. Take fresh screenshots after meaningful changes and
repair specific defects rather than restarting the design. The component workflow
owns recovery and synchronization; do not create a competing one.

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
widths, not just breakpoint tokens. Check semantics, keyboard behavior,
accessibility, and interactions in code; Paper input frames do not supply them.
Snapshot can bring the rendered implementation back as editable comparison
material, but is not lossless component or theme round-trip synchronization.

## Recovery

Wrong document: read identity before more writes. Visible tools but failed canvas
reads: check Desktop and file availability, then transport/host state. For stale
sessions, rediscover schemas; an agent restart or host MCP toggle may be needed.
Updated Pro limits may require updating/restarting Desktop. WSL may need mirrored
networking; see `canvas-and-support.md`. Coordinate disruptive changes and do not
repeatedly retry a dead screenshot session.
