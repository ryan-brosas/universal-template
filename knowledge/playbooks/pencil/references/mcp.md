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
If unavailable, report the constraint; substitute only with explicit user acceptance
and use `approved-fallback`, never `pixel-perfect` (`completion-contract.md`).
Do not add a caption absent from the source to conceal the substitution.
