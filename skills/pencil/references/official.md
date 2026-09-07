# Paper platform documentation

The canonical Paper docs guide is now `../../paper-design/SKILL.md`, with the
complete official source map and review date in
`../../paper-design/references/index.md`. Load only the relevant capsule:

- `../../paper-design/references/themes-and-tokens.md`: Theme UI, CSS variables,
  aliases, copy to code/files, current mode/library boundaries.
- `../../paper-design/references/figma-and-html-import.md`: editable clipboard
  imports, Figma slots, image authorization, translation losses, HTML rules.
- `../../paper-design/references/mcp-and-handoff.md`: connections, operations,
  Figma/content/code workflows, recovery.
- `../../paper-design/references/canvas-and-support.md`: vectors, Snapshot/CORS,
  shortcuts, troubleshooting.
- `../../paper-design/references/improvement-loop.md`: release-driven experiments
  and measured improvements to transfer/reuse.

Pencil still owns literal transfer and `tokens.md` owns source identity, bindings,
mode mapping, and safe propagation. Paper component consistency owns structural
reuse. Current documentation and verified installed behavior outrank old capability
snapshots; specifically, Figma paste detachment does not mean Paper lacks tokens.

Official entry: [paper.design/docs](https://paper.design/docs).
