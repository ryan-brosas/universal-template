# MCP probe for Pencil

## Probe, then call

1. Search the MCP registry for `paper_` and `figma`.
2. Paper Desktop must have the target file open. MCP talks to that file. Confirm with `get_basic_info`. Long agent sessions go stale ([docs/mcp](https://paper.design/docs/mcp), [docs/support](https://paper.design/docs/support)): restart the session, do not keep retrying dead tools.
3. Paper: `get_guide` topic `figma-import` once per session, then `create_tokens`, `create_artboard`, `write_html`, `duplicate_nodes`, `get_screenshot`, `finish_working_on_nodes`.
4. Figma: `figma-bridge` `get_variable_defs` (before tokens; select a node that has the variable assigned), `save_screenshots`, `get_node`, `get_metadata`. Official `get_design_context` if it authorizes. If it returns Unauthorized, stay on the bridge; do not invent.
5. Assets and library reuse: `figma-console` (Southleft, local mode) reaches what the bridge cannot — published-library components and variables over the Figma REST API, plus plugin-side console telemetry. Two prerequisites: the Desktop Bridge plugin running from `~/.figma-console-mcp/plugin/manifest.json` for live-document tools (without it, calls report `transport.active: none` rather than failing loudly), and `FIGMA_ACCESS_TOKEN` in the host config for the REST path. `figma_get_library_variables` stays plugin-only.
   - Discover, then place. `figma_search_components` / `figma_get_library_components` with a `libraryFileKey` return keys for that library's component sets. A readable file with nothing published answers with an empty `totalComponentSets`; a 404 means the key is not readable at all. Neither is a broken token, so read the error shape before blaming credentials.
   - Place with `figma_instantiate_component`, or inside `figma_execute` with `figma.importComponentSetByKeyAsync(key)` followed by `variant.createInstance()`. Prefer instantiating a real library component over redrawing it from primitives, and confirm `mainComponent.remote === true` with a resolvable key before calling the asset linked.
6. Large or deep Figma trees error. Split by frame or variant. Figma MCP often returns SVG fills as images and drops spacer frames; screenshot is still ground truth.

## Published libraries

A file's Assets panel, not its canvas, is the source of truth: a canvas can hold zero
components while three libraries are enabled.

**`figma_get_library_variables` does not name every enabled library.** It wraps
`figma.teamLibrary.getAvailableLibraryVariableCollectionsAsync()`, the plugin API's only
library enumeration, and that lists variable collections alone. A component-only kit
returns `0` collections and `0` variables while being fully enabled. Verified 2026-09-17:
an enabled 1,082-set icon and UI library read as zero, and that zero was reported to the
user three times as "nothing was added"; the library was only proven present by an instance
already placed from it. Read the result as "no subscribed library exposes variables", never
as absence of libraries.

Recover the file key from the document rather than from desktop history. Place or find one
instance of anything from the library, then:

1. `getMainComponentAsync()` on the instance gives `mainComponent.key`. Use the async
   accessor; `node.mainComponent.key` is null for remote components in dynamic-page mode.
2. `figma_get_library_component_by_key({ componentKey })` returns `fileKey`, `nodeId`, the
   containing frame and page, and the key's variants. `Component key not found` is a
   not-found, not a credential failure.
3. `figma_get_library_components({ libraryFileKey })` returns the catalogue, 25 entries per
   call with `pagination.hasMore`; `libraryFileUrl` is the alternative and one of the two is
   required.
4. `figma_get_file_data({ fileUrl })` names the library, which is how you confirm which
   enabled library you are holding. It takes a URL or URI, not `fileKey`.

Instantiate a **variant** key (type `COMPONENT`), never the component-set key. To find a set
by name without paging the catalogue, pass `query` to `figma_get_library_components` or
`libraryFileKey` to `figma_search_components`. A raw `fetch` to
`api.figma.com` from inside `figma_execute` failed when tested (CORS or sandbox policy was
not isolated), so route REST calls through the MCP tools rather than the sandbox.

With no instance and no URL, no tool lists libraries or their keys. Fall back to the desktop
client's own state — recent tabs, browser or shell history — and verify each candidate with
`figma_get_library_components`: a readable library answers with its component count, while a
wrong key answers `0` with `apiErrors` rather than throwing.

To prove a placed asset's provenance, resolve its key back to the owning file and name
(`figma_get_library_component_by_key`, then `figma_get_file_data`). `remote: true` alone
only says it came from some library, not which one.

Identify the owning library before composing. Resolve a placed instance's bound variables
(`node.boundVariables` → `figma.variables.getVariableByIdAsync` → `variableCollectionId` →
collection name) and match that name against
`getAvailableLibraryVariableCollectionsAsync()`. An instance bound to `📐 Space`,
`🟢 Radius` and `🌈 Theme` belongs to Atomize PRO whatever the file is called. That
route needs a library that exposes variables; for a component-only kit use the key
chain above. Bind new containers to those same collections via `figma.variables.importVariableByKeyAsync(key)` so
the tokens stay linked instead of copied.

Cold imports from a large library can exceed the bridge timeout. Confirm a single import
before batching more; a timeout alone does not establish whether the document changed.
`importComponentSetByKeyAsync` on the set key provides access to its variants. Instances
reject new children, so place them as siblings inside a layout-only frame rather than
detaching an artboard to hold content. Component operations can fail on an `unloaded font`;
load the required font or report the gap rather than substituting an unapproved lookalike.

Compose `figma_execute` payloads as an array of single-line strings joined by newlines.
Template literals that embed quotes, brackets and em dashes are where sandbox syntax errors
come from, and a TypeScript annotation inside the payload fails as a sandbox syntax error
rather than a type error. Building the code line by line also makes it obvious when draft
debris is still in it.

## Recover partial operations

An outer `success: true` means the script returned, not that every requested item worked.
Inspect per-item `err`/`apiErrors` and expected results even when `resultAnalysis.warning`
is null. Separate successful items from failed or unknown ones before proceeding.

After an error or timeout, inspect the target and surrounding canvas before retrying.
Use node IDs recorded during creation to reconcile what exists; do not replay the whole
batch and duplicate successful work. Clean only identified scratch artifacts within the
authorized scope; preserve nodes of uncertain ownership. Retry incomplete items only
after resolving the blocker and checking whether the earlier operation is still running.

Read back the repaired state and take a fresh render. If a containment audit fails,
compare bounds in one coordinate space before moving nodes: parent-relative positions
compared with canvas positions can falsely flag a correctly placed frame.

## Customize assets and verify the visible result

For original website composition (not exact reproduction), first use
[Website visual direction](../../ui-ux-iteration-loop/references/loop-variants-and-gates.md#website-visual-direction).

For an independent attempt, compose from source assets rather than cloning the previous
output and calling it a new direction. For refinement, reuse the existing composition;
the independent-attempt correction is not a general ban on cloning.

Library defaults are starting points, not requirements. Within the approved brief,
mix suitable assets and adapt variants, text, typography, color, spacing, and optional
slots. Inspect exposed properties first: remove irrelevant navigation icons, emojis,
secondary labels, and actions through component properties rather than detaching.
Inspect the resulting render; successful property writes can leave nested overrides
unchanged. Correct remaining range-level text/paint overrides at their owning node.

When project-specific token customization is authorized, derive an editable project
collection from source variables and record source keys and intentional changes.
Preserve mode and alias meaning; document any deliberate simplification rather than
silently flattening it. Test resolved values on actual consumers, not token names:
a plausible typography token can resolve to the wrong size or mode. Bind customized
values instead of scattering raw overrides, and verify fonts actually render.

Keep provenance and presentation checks separate. Resolve component masters and
bindings inside the requested deliverable, not just a nearby asset demonstration.
A successful import proves the capability, not that the homepage uses it. Report visible
deliverable coverage separately from hidden/archive content and nested-instance totals.
Hundreds of linked instances prove neither visual quality nor user acceptance.
Take a fresh render after the final fix; check optional
content, text contrast, wrapping, clipping, alignment, and section duplication.
A single inspected image or canvas search does not exhaust enabled libraries or
user-owned marketplace assets. State the search boundary before declaring a gap.

## Screenshots

- `save_screenshots` paths must sit inside the Figma bridge working directory (often the user home). `/tmp` is rejected.
- Export IMAGE fills and VECTOR icons as PNG/SVG. Use `paper-asset://` + absolute path in Paper HTML.
- A full component-set PNG can be huge; export the set, then individual variants for detail.

## get_node

- Page IDs list frames. Component-set children are variants (`Type=primary, Size=md, State=default`).
- Adapter text may truncate. Do not parse the displayed prefix as a complete tree.
  Inspect the adapter’s saved complete response when available, extracting only
  relevant nodes and retaining source identity/counts. Otherwise fetch a bounded
  frame or variant rather than replaying the full set. A local walker can reduce
  context; it must not invent missing variants or silently narrow requested scope.

## Timeouts

- One visual row per `write_html`.
- Do not inline the same SVG path on every button; export one file and reuse `paper-asset://`.
- Paper `get_screenshot` of a 3000px-tall artboard can time out; screenshot the row you just wrote.

## Fonts

Use font inventory as a preflight signal, then verify the intended family renders.
A text node holding more than one font reports `fontName` as `figma.mixed`, which
`JSON.stringify` renders as `undefined`; that is not a missing font. Walk the node's ranges
with `getRangeFontName` instead, or the fonts inside mixed nodes stay invisible to the
inventory, and those nodes are exactly where a template keeps its specimen and placeholder
text. Confirm a weight by loading it (`loadFontAsync` rejects with "could not be loaded"),
not by reading a style list.
If unavailable, report the constraint; substitute only with explicit user acceptance
and use `approved-fallback`, never `pixel-perfect` (`completion-contract.md`).
Do not add a caption absent from the source to conceal the substitution.
