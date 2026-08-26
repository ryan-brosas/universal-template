<!-- capsule-v2 -->
# Editor safety seams — where does a 2,300-line terminal editor keep its correctness?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter builds a terminal text editor and loses drafts, applies stale suggestions, or breaks cursor position on wrapped lines — which seams matter?

## Atomic pastes, snapshot-validated async suggestions, draft-preserving history
**Path/Symbol:** `packages/tui/src/components/editor.ts` (2,363L).
**Signature:** paste → ATOMIC marker segments with valid ids; autocomplete request → serialized behind a monotonic `startToken` with a full (text, line, col) snapshot validated on completion; history browse → snapshot-clone of the draft restored exactly on return.
**Data Shape:** Segmentation merges only currently-valid marker ids, so undone pastes degrade to plain text gracefully; cursor snaps to segment starts with `snappedFromCursorCol` remembering the pre-snap column; an atomic segment wider than the terminal re-wraps at grapheme granularity but stays "logically atomic for cursor movement/editing — the split is purely visual." Sticky `preferredVisualCol` preserves horizontal position across wrapped-line vertical moves. Kill-ring + lastAction classification powers yank-pop; ctrl+] jump mode rounds out Emacs muscle memory.

### Decisive source
```ts
// Autocomplete serialization (pattern): every request captures
//   { startToken: monotonic++, text, line, col }
// On completion: if startToken !== current.startToken → STALE, discard.
// Single-result Tab applies directly AFTER pushing an undo snapshot.
```
Large pastes become atomic markers; undo of a paste degrades content but keeps ids valid because only currently-valid ids merge.

**Flow:** paste → segment atomically → edit/move within logical units regardless of visual wrapping → suggestion requests serialize and self-invalidate → Tab applies with undo pushed first → history navigation never destroys an unsent draft.
**Invariant:** Editor correctness lives at the seams, not in the render loop: (1) pastes are single undo/cursor units even when visually split; (2) no stale async completion may ever mutate text that changed since its request; (3) browsing history must restore the in-progress draft byte-for-byte.
**Probe:** `packages/tui/test/editor.test.ts` + `packages/tui/test/editor-history-keybindings.test.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "editor atomic paste startToken preferredVisualCol", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt all three seams as a set — they interlock. Adapt key choices to your muscle-memory targets. Omit kill-ring if you ship no Emacs duality. Coverage caveat: none.
