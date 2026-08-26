<!-- capsule-v2 -->
# Cached-statement release — why must COUNT lookups not park on their result row?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How does statement caching deadlock a WAL↔DELETE journal switch, and what's the fix?

## Reset-before-park rule for cached statements
**Path/Symbol:** `src/store/store.c` prepare_cached discipline + tests/test_store_checkpoint.c:232 (`cached_count_queries_release_delete_mode_reader_lock`), 268 (`cached_node_lookups_release_delete_mode_reader_lock`).
**Signature:** cached statements must be sqlite3_reset() before returning to the cache — never left mid-iteration.
**Data Shape:** Scenario: index_repository opens a QUERY connection to verify a newly published DELETE-mode DB; if a cached COUNT stays parked on SQLITE_ROW it holds a read txn; the next writer then CANNOT switch the DB back to WAL.

### Decisive source
```c
/* index_repository opens a query connection to verify the newly published
 * DELETE-mode DB. Cached COUNT statements must not remain parked on their
 * result row, otherwise a following writer cannot switch the DB back to WAL. */
cbm_store_t *reader = cbm_store_open_path_query(db_path);
ASSERT_EQ(cbm_store_count_nodes(reader, "count_lock"), 1);
...
cbm_store_t *writer = cbm_store_open_path(db_path);  /* must succeed */
```

**Flow:** count/lookup helpers use prepared-cache → drain rows → RESET (not just finalize at close) → return to cache → writer's journal-mode PRAGMA succeeds.
**Invariant:** Any statement cache in SQLite needs this rule; parking is invisible until a journal switch or checkpoint hangs.
**Probe:** the two named tests plus seal twins (151/183) and stale-sidecar pair (344/417).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "prepare_cached", limit: 5 });
```

## Verdict
Adopt reset-before-cache-return for every statement cache; adapt to your wrapper; test with an explicit journal-switch sequence like this one.
