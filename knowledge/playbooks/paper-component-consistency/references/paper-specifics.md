# Paper-specific operating notes

## Connection and capability boundaries

Paper can target multiple open files, including background tabs. Pass explicit file
identity where supported and reconfirm page context after switching or reconnecting;
a remembered node ID does not identify the intended workspace. Use the live host
connection and schemas, not a copied tool inventory.
For Theme UI/CSS-variable mechanics, imports, Snapshot, and current platform
capabilities, load `../../paper-design/README.md`. Its improvement loop supplies
bounded release-driven experiments without replacing component ownership.

A missing or failing operation may indicate a stale session rather than an absent
feature. Inspect connection health and retry a small read after reconnecting. If
necessary, ask the user to restart the agent session or toggle Paper MCP. If access
remains unavailable, report the block rather than claiming canvas verification.

Prefer an existing official plugin or verified host connection. Use a configured
registry fallback only when no connection already owns Paper; do not register a
second server. Ordinary Paper work needs no Figma connection. Transport setup is
not a component-management prerequisite.

## Efficient mutations

- Deep duplication is a copy, not proof of linked-instance semantics. Native
  definitions, instances, overrides, variants, and slots may arrive independently;
  choose supported mechanisms per operation, without assuming the rest exist.
- Duplication returns new IDs and a descendant mapping. Retain that result for
  content substitution and verification within the current operation.
- Batch text/style changes and computed-style reads where the live schema allows.
  Partition large trees into bounded groups; a truncated response is incomplete
  evidence, not an empty or missing consumer set.
- After a timeout, inspect the affected scope before retrying: a mutation may have
  completed. Saved JSX and screenshots are recovery evidence, not guaranteed
  lossless backups; preserve originals until replacements are verified.

## Verify normalized styles

Paper may normalize requested CSS into a different representation. In an observed
single-line truncation case, `textOverflow: ellipsis` was read back as a one-line
WebKit clamp with hidden overflow. A missing original property alone did not mean
the update failed. Inspect the returned compound styles and a fresh long-label
render before retrying or rebuilding. Actual wrapping, clipping, or displaced
siblings still fails the slot contract; this is not universal CSS equivalence.
Keep token-reference checks separate: normalization is not permission to replace
an intended binding with an equal literal value.

Source: [official Paper MCP documentation](https://paper.design/docs/mcp).
Consult current documentation when connection behavior or capabilities differ;
the live schema owns tool names, arguments, and return shapes.
