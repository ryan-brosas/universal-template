<!-- capsule-v2 -->
# Hunk-scoped impact seeds — how do you limit blast-radius analysis to the functions a diff actually touched?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How does detect_changes seed BFS from edited SYMBOLS instead of whole files, without regressing on new files?

## Line-overlap probe with structural-label exclusion
**Path/Symbol:** `src/mcp/mcp.c:cbm_detect_node_in_hunks` (10381–10390) + `detect_collect_seeds` (10411–10440) + `detect_is_seedable_label` (10405–10409).
**Signature:** `bool cbm_detect_node_in_hunks(const cbm_node_t *node, const cbm_changed_hunk_t *hunks, int hunk_count, const char *file);`
**Data Shape:** Overlap test: same path AND `node.start_line <= hunk.end_line && node.end_line >= hunk.start_line`. Seedable labels exclude File/Folder/Project/Module/Package/Section (containers carry no CALLS edges).

### Decisive source
```c
/* When `hunks` has at least one entry for `file`, only definitions whose line
 * range overlaps a hunk become seeds — a one-line edit inside a single
 * function no longer seeds every other definition in the file. When no hunk
 * is recorded for `file` ... every non-container definition in the file is a
 * seed — the previous, whole-file behavior — so this is a precision
 * improvement, not a new failure mode. */
```

**Flow:** parse git diff into per-file hunks → for each changed file collect its nodes → if any hunk exists for the path, filter to overlapping non-container defs; otherwise keep all defs → multi-source BFS over CALLS/USAGE edges yields impacted symbols → response reports blast radius with per-action ledger.
**Invariant:** The no-hunk fallback is REQUIRED (new/untracked files have no before-state); scope must never widen silently from symbol-level back to file-level.
**Probe:** `tests/test_mcp.c:detect_changes_node_in_hunks_overlap_issue1363` (inside/exact/touching-edge match; before/after/wrong-file don't) and `detect_changes_seeds_only_touched_symbol_issue1363` (editing foo() must not seed bar()).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_detect_node_in_hunks", limit: 5 });
```

## Verdict
Adopt overlap-seeded traversal with the explicit fallback ladder; adapt hunk parsing to your VCS; omit the include-tests toggle if your consumers always want full radius.
