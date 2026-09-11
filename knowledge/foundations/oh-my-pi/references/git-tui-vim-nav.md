<!-- capsule-v2 -->
# Vim-navigation & focus contract — how does a two-pane TUI share vim motions, hunk-edge file rollover, and a dimmed-cursor focus signal across diff and sidebar?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** How do `jumpHunk`/`seekHunk`/`cursorToEdge` compose so hunk navigation rolls into the adjacent FILE at the edges instead of dead-ending?

## Edge-rolling navigation primitives
**Path/Symbol:** `packages/coding-agent/src/cli/git-tui/diff-pane.ts:` `jumpHunk(direction)` (364b63822f, :~560–590 at pin), `seekHunk(edge)` + `cursorToEdge(edge)`, `#focusHunkHeader`, `#changeStarts`; controller wiring `index.ts` (`#pendingHunkEdge` @:438, focus toggle @:391–394/:449, keymap doc-comment :10–18); sidebar actions `sidebar.ts`.
**Signature:** `jumpHunk(direction: 1 | -1): boolean` — false ONLY when already at the boundary; `cursorToEdge(edge: "start" | "end"): void`.
**Data Shape:** Focus = `"diff" | "sidebar"`; pending-hunk-edge handoff `{direction}` consumed after the file switch completes.

### Decisive source
```ts
// Other modes: jump between change blocks.
const starts = this.#changeStarts(visuals);
const next = direction > 0
	? starts.find(start => start > reference)
	: [...starts].reverse().find(start => start < reference);
if (next === undefined) return false;      // caller rolls into the adjacent file
...
/** Move the cursor to the first/last visual row (home/end, g/G). */
cursorToEdge(edge) { ...; this.anchor = null; this.cursor = edge === "start" ? 0 : total - 1; ... }
```

**Flow:** alt+↓/↑ in the pane → hunk view steps selected hunks; other modes jump change-block starts → at boundary `jumpHunk` returns false → controller sets `#pendingHunkEdge` and calls `sidebar.selectAdjacentFile(direction, current)` → after the new file's document loads, the pending edge lands via `seekHunk("first"/"last")` — "the landing spot when hunk nav crosses files". Vim motions j/k/h/l/g/G work in BOTH panes; `]`/`[` switch files; 1–4 pick views directly; space pages. Focus is signaled by `pane.focused` AND `sidebar.setFocused`, with the diff cursor band DIMMED in unfocused panes (a4cffcd778-era polish).
**Invariant:** Navigation booleans are contracts: returning false means "boundary reached, host may roll over" — never silently clamp inside the pane. Selection anchor clears on edge jumps (`this.anchor = null`) so shift-extended ranges don't survive teleports. The pending-edge handoff must survive the async document swap but be consumed exactly once.
**Probe:** No dedicated unit test for the nav layer (interactive); behavior verified by read at pin: boundary-false arms and seekHunk landing byte-exact in diff-pane.ts; CHANGELOG contract line ("alt+↓/alt+↑ jump hunks and roll into the adjacent file at the edges") matches implementation. Deterministic grep: `#pendingHunkEdge` @index.ts:438. Runner caveat as recorded.
**Omitted-with-reason:** full sidebar stage/unstage form plane (commit-form internals are product surface beyond this seam).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "jumpHunk seekHunk cursorToEdge", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69 via search_code line-exact (nav methods resolve under the diff-pane family; BM25 multi-symbol query returns sibling render methods — use the single-symbol fallback `jumpHunk` if needed).

## Verdict
Adopt boolean-boundary jump primitives with a host-level roll-over latch for any paged/multi-document viewer; keep anchor-clearing on teleports. Adapt keymap to your host. Omit mouse-wheel and theme details.
