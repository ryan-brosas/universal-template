<!-- capsule-v2 -->
# Bulk write pragmas — how do you speed up massive inserts while keeping WAL mode and crash recovery intact?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Which pragmas may begin_bulk relax, and what must end_bulk (or a crash) restore?

## WAL invariant across bulk begin/end/crash
**Path/Symbol:** `src/store/store.c:cbm_store_begin_bulk` / `cbm_store_end_bulk` + `src/pipeline/pipeline_incremental.c` merge tail; pinned by tests/test_store_bulk.c.
**Signature:** `int cbm_store_begin_bulk(cbm_store_t *s);` / `int cbm_store_end_bulk(cbm_store_t *s);`
**Data Shape:** During bulk: journal_mode MUST remain WAL; synchronous may drop to OFF for the load; explicit transaction wraps batches. End restores NORMAL synchronous. A crashed child (`_exit()` mid-transaction) must leave committed baselines intact and uncommitted rows absent.

### Decisive source
```c
TEST(bulk_pragma_wal_invariant) {
    char *before = get_journal_mode(db_path);
    ASSERT_STR_EQ(before, "wal");
    int rc = cbm_store_begin_bulk(s); ASSERT_EQ(rc, CBM_STORE_OK);
    char *after = get_journal_mode(db_path);
    ASSERT_STR_EQ(after, "wal"); /* FAILS with bug, PASSES with fix */
```

**Flow:** open (WAL) → begin_bulk drops synchronous inside one transaction → batched node/edge/hash upserts → end_bulk re-raises durability and leaves journal_mode WAL → crash path relies on SQLite rollback of the uncommitted txn with sidecar cleanup on next open.
**Invariant:** Never switch to MEMORY/DELETE journals for bulk loads here — sibling readers depend on WAL semantics; durability relaxation is scoped strictly between begin/end.
**Probe:** `tests/test_store_bulk.c:bulk_pragma_wal_invariant`, `bulk_pragma_end_wal_invariant`, `bulk_crash_recovery` (fork+`_exit()` mid-bulk).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_begin_bulk", limit: 5 });
```

## Verdict
Adopt "relax only synchronous, never journal_mode" for bulk loaders sharing a WAL DB; adapt batch sizes; omit the fork-based crash test if your CI lacks POSIX processes.
