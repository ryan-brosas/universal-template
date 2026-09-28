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

**Paper → application:** use the [live-source-first handoff](#paper-to-code-live-source-first)
below. Snapshot can bring the rendered implementation back as editable comparison
material, but is not lossless component or theme round-trip synchronization.

## Paper-to-code: live source first

Use for implementing a Paper design or feedback that the agent is ignoring Paper.
Code-only logic or dependency fixes with no changed visual contract do not need a
canvas preflight. Application architecture remains the frontend workflow's concern.

### Before visual code edits

1. **Confirm the live target.** Use `get_basic_info` and a bounded tree read to
   identify the file, page and relevant desktop/mobile viewport frames. A presentation
   wrapper containing both screens is not an application viewport. Local route maps
   help locate frames; confirm them through Paper rather than trusting old IDs.
2. **Read the affected section directly.** Inspect `get_jsx`,
   `get_computed_styles` and a source `get_screenshot` (or supported equivalents).
   Read relevant tokens and stored bindings using [themes-and-tokens.md](themes-and-tokens.md);
   resolved CSS alone does not prove alias or mode provenance. Inspect original
   images/vectors used by the section through available asset/export tools. Bound reads to the
   section and its layout context, not the entire file.
3. **Reconcile intent and ownership.** Map the source section to existing code
   components, assets and token/style owners. Check current requirements and
   documented approved differences, including repaired source assets. Do not
   silently normalize the design or copy known-broken imports back over repairs.
   If the requested fidelity conflicts with an approved exception, ask which wins
   before changing the affected property.
4. **State the handoff before editing.** Briefly report the confirmed file/page/frame
   IDs, successful live reads and source render, target code owners, and retained
   exceptions or blockers. Reuse still-valid live reads from this task; refresh
   affected evidence when the design changes. Token hashes cover tokens, not the
   whole frame's freshness.

Local documentation, Sourcebot/code search and prior descriptions are navigation
aids, not substitutes for direct Paper inspection. If a required live read fails,
name the failed operation and stop source-dependent edits rather than reconstructing
from memory. An explicitly user-approved snapshot handoff is a valid exception;
label it snapshot-based, not live-Paper verification. Keep Paper read-only unless
design-file changes are separately authorized.

### Implement and compare

Translate one bounded section into the existing stack and component/token owners.
Exported JSX is source evidence, not a drop-in application or permission to generate
a parallel React app inside an Astro project. Preserve asset provenance and token
aliases; do not replace them with guessed artwork or a second theme.

Use the project's preview and focused tests. Compare the affected browser render
with the inspected Paper render at matching viewport widths after fonts and images
load; check actual font delivery if metrics differ. Inspect geometry, text wrapping,
crops and responsive reflow, then probe intermediate widths and application-only
semantics, keyboard behavior and interactions. Explain approved differences instead
of hiding them in new baselines. Report source IDs, changed code paths, comparisons
and remaining gaps. Passing tests, exported JSX or a dev URL alone do not prove
visual fidelity or deployment.

## Recovery

Wrong document: read identity before more writes. Visible tools but failed canvas
reads: check Desktop and file availability, then transport/host state. For stale
sessions, rediscover schemas; an agent restart or host MCP toggle may be needed.
Updated Pro limits may require updating/restarting Desktop. WSL may need mirrored
networking; see `canvas-and-support.md`. Coordinate disruptive changes and do not
repeatedly retry a dead screenshot session.
