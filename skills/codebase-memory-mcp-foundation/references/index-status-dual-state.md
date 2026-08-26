<!-- capsule-v2 -->
# index_status freshness — how do you answer "is this index current?" in one call?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What does the status tool report, and how do agents use it to decide reindex?

## HEAD + dirty flag + counts + generation in one row
**Path/Symbol:** `src/store/store.c:cbm_store_get_index_status` (~7800s) + tests/test_store_arch.c (`store_get_index_status`, 503+); watcher integration via baselines.
**Signature:** `int cbm_store_get_index_status(cbm_store_t *s, const char *project, cbm_index_status_t **out);`
**Data Shape:** Reports stored git HEAD at last index, whether worktree is now dirty relative to it, node/edge/file counts, generation number, and coverage summary pointers — everything a client needs to choose NOOP vs incremental vs full.

### Decisive source
```c
TEST(store_get_index_status) { ... }
```

**Flow:** read project row + store_meta generation + git context (current HEAD/dirty) → diff against stored baseline → emit verdict-shaped status. The closure-repair planner consumes exactly these inputs.
**Invariant:** Status must reflect STORED state and LIVE git state separately — conflating them hides drift.
**Probe:** the named test; consumer behavior in tests/test_incremental.c route assertions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_get_index_status", limit: 5 });
```

## Verdict
Adopt dual-state (stored vs live) status endpoints for any indexed cache; adapt fields; feed the same struct to your incremental planner.
