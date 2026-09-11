# MCP probe for Pencil

## Probe, then call

1. Search the MCP registry for `paper_` and `figma`.
2. Paper Desktop must have the target file open. MCP talks to that file. Confirm with `get_basic_info`. Long agent sessions go stale ([docs/mcp](https://paper.design/docs/mcp), [docs/support](https://paper.design/docs/support)): restart the session, do not keep retrying dead tools.
3. Paper: `get_guide` topic `figma-import` once per session, then `create_tokens`, `create_artboard`, `write_html`, `duplicate_nodes`, `get_screenshot`, `finish_working_on_nodes`.
4. Figma: `figma-bridge` `get_variable_defs` (before tokens; select a node that has the variable assigned), `save_screenshots`, `get_node`, `get_metadata`. Official `get_design_context` if it authorizes. If it returns Unauthorized, stay on the bridge; do not invent.
5. Large or deep Figma trees error. Split by frame or variant. Figma MCP often returns SVG fills as images and drops spacer frames; screenshot is still ground truth.

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
