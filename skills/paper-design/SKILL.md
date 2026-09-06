---
name: paper-design
description: "Use when working with Paper's documented features, themes and CSS-variable tokens, Figma or HTML paste, SVG editing, MCP setup, Snapshot, or checking new Paper capabilities. Supplies platform mechanics; pencil owns exact Figma transfer."
invocation: manual
disable-model-invocation: true
---

# Paper Design

Turn Paper's documented capabilities into a working design/code workflow. This is
an on-demand guide to the complete official docs set, not a second fidelity or
component-management procedure. Load only the relevant reference.

## Choose the work

| Need | Read |
|---|---|
| Theme UI, CSS variables, aliases, code synchronization, modes | `references/themes-and-tokens.md` |
| Figma clipboard, images, slots, translation losses, HTML | `references/figma-and-html-import.md` |
| Agent connection, tool selection, safe batching, code handoff | `references/mcp-and-handoff.md` |
| SVG editing, Snapshot/CORS, shortcuts, troubleshooting | `references/canvas-and-support.md` |
| New capabilities or repeated transfer problems | `references/improvement-loop.md` |
| Full docs coverage and source freshness | `references/index.md` |

For exact Figma transfer, use `../pencil/SKILL.md`; for fidelity diagnosis, use
`../pixel-perfect/SKILL.md`. Their ownership and fidelity gates still apply. Application implementation belongs to the project's frontend workflow.

## Useful defaults

- **Choose the cheapest faithful input.** Direct Figma paste produces editable
  layers; use it as a candidate fast path, then inspect losses. Use MCP to recover
  source semantics, repair bindings, and handle targeted reconstruction. HTML and
  Snapshot are separate import paths with different limitations.
- **Make the theme functional.** Reuse or create the required file tokens and bind
  actual properties with CSS variables. A swatch sheet, matching literal, or pasted
  Figma variable name does not prove a binding.
- **Keep two-way edits deliberate.** Figma, Paper, and code can each supply values;
  choose the authoritative owner for this task. Copying tokens is not continuous
  synchronization, and copying components is not linked instancing.
- **Check current capabilities at the affected boundary.** These sources were read
  on 2026-09-06. A release note proves an announcement, a schema proves an exposed
  operation, and a disposable runtime probe proves behavior. Do not equate them.
  Installed guides can conflict with token tools; see the documented conflict notes.
- **Improve from evidence.** After a meaningful transfer failure or Paper update,
  compare one representative fixture, keep the smallest improvement, and update
  the existing owner. No daemon, automatic document mutation, or recurring report
  is required.

## Completion evidence

For feature advice, distinguish documented, schema-inspected, and runtime-tested
claims. For design changes, report destination IDs, inspected bindings and assets,
actual visual checks, unsupported translations, and untested modes. Use the
existing Pencil fidelity gate before claiming an exact transfer. A breakpoint
token is not responsive behavior; a canvas render is not an accessible application.
