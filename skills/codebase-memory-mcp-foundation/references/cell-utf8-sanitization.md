<!-- capsule-v2 -->
# Cell UTF-8 sanitization — why does ONE bad byte poison an entire tool output?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What must cell emission guarantee so line-oriented consumers never see binary garbage?

## Escape controls as \\u00XX, invalid bytes → U+FFFD, force-quoted
**Path/Symbol:** `src/mcp/mcp.c:cbm_tree_cell_str` + tests/test_mcp.c:631 (`tree_cell_sanitizes_control_and_invalid_utf8`).
**Signature:** `void cbm_tree_cell_str(cbm_sb_t *sb, const char *val, bool first);`
**Data Shape:** Any control byte or invalid UTF-8 ⇒ the WHOLE cell is emitted in QUOTED form with controls escaped (`\\u0001`) and invalid sequences replaced by U+FFFD; valid UTF-8 stays raw and unquoted.

### Decisive source
```c
/* One raw control or invalid-UTF8 byte in a cell poisons LINE-ORIENTED
 * consumers of the ENTIRE output (BSD grep treats all of it as unmatchable
 * binary — the macos-15-intel release-smoke B3 class), so cell emission
 * guarantees valid UTF-8 ... */
cbm_tree_cell_str(&sb, "evil\x01name\xff" "end", true);
ASSERT_STR_EQ(out, "\"evil\\u0001name\xEF\xBF\xBD" "end\"");
```

**Flow:** per-cell scan → dirty? quote+escape : pass through → identifiers from arbitrary repos WILL contain weird bytes eventually, so this is load-bearing not cosmetic.
**Invariant:** Sanitization granularity is the CELL (smallest emit unit) — one bad byte must degrade only its own cell, never the row/table.
**Probe:** `tests/test_mcp.c:tree_cell_sanitizes_control_and_invalid_utf8`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_tree_cell_str", limit: 5 });
```

## Verdict
Adopt cell-level UTF-8 guarantees for any text pipeline feeding line tools; adapt escape style; remember WHY (grep binary detection).
