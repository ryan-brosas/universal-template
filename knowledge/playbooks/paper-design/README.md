---
title: paper-design
summary: Use when implementing Paper designs in code, using themes and CSS-variable tokens, Figma or HTML paste, SVG editing, MCP setup, Paper desktop updates or startup/scaling troubleshooting, Snapshot, or checking new capabilities. Owns Paper workflow and runtime guidance; pencil owns exact Figma transfer and paper-component-consistency owns reusable composition.
kind: playbook
---

# Paper Design

Use Paper's documented capabilities and diagnose its desktop runtime. Load only
the relevant reference; this guide does not replace fidelity or component-management
procedures. Desktop maintenance does not require a canvas-editing workflow.

## Choose the work

| Need | Read |
|---|---|
| Theme UI, CSS variables, aliases, code synchronization, modes | `references/themes-and-tokens.md` |
| Figma clipboard, images, slots, translation losses, HTML | `references/figma-and-html-import.md` |
| Paper-to-code, agent ignoring the live design, implementation from Paper | [Live-source-first handoff](references/mcp-and-handoff.md#paper-to-code-live-source-first) |
| Agent/CLI connection, tool selection, safe batching | `references/mcp-and-handoff.md` |
| Desktop update/reinstall, Linux AppImage startup, interface scale versus canvas zoom | [Desktop runtime](references/desktop-runtime.md) |
| SVG editing, Snapshot/CORS, shortcuts, troubleshooting | `references/canvas-and-support.md` |
| New capabilities or repeated transfer problems | `references/improvement-loop.md` |
| Full docs coverage and source freshness | `references/index.md` |

For exact Figma transfer, use `../pencil/README.md`; for reusable Paper composition,
use `../paper-component-consistency/README.md`. Their ownership and fidelity checks
still apply. Application implementation belongs to the project's frontend workflow.

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
- **Check current capabilities at the affected boundary.** See `references/index.md`
  for source freshness. A release note proves an announcement, a schema proves an
  exposed operation, and a disposable runtime probe proves behavior. Do not equate
  them. Cached pages and installed guides can lag the live docs and token tools;
  check the nearest source before retaining a limitation.
- **Improve from evidence.** After a meaningful transfer failure or Paper update,
  compare one representative fixture, keep the smallest improvement, and update
  the existing owner. No daemon, automatic document mutation, or recurring report
  is required.

## Completion evidence

For desktop maintenance, use the [restart and scaling checks](references/desktop-runtime.md#verify-the-restart).

For feature advice, distinguish documented, schema-inspected, and runtime-tested
claims. For design changes, report destination IDs, inspected bindings and assets,
actual visual checks, unsupported translations, and untested modes. Use the
Pencil completion evidence before claiming an exact transfer. A breakpoint
token is not responsive behavior; a canvas render is not an accessible application.
