<!-- capsule-v2 -->
# Coverage replace transaction — why does a 9-second coverage rewrite need sub-block timing and a NOT-IN prune?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you atomically replace per-file coverage rows at scale while keeping observability into WHERE the time went?

## BEGIN/DELETE/insert-batch/prune/meta/COMMIT with cov_ms[5] ledger
**Path/Symbol:** `src/store/store.c:cbm_store_coverage_replace_ex` (2918–3050).
**Signature:** `int cbm_store_coverage_replace_ex(cbm_store_t *s, const char *project, const cbm_coverage_row_t *rows, int count, const cbm_coverage_meta_t *meta);`
**Data Shape:** One transaction: DELETE FROM index_coverage WHERE project → INSERT OR REPLACE per row (13k rows with large error_ranges payloads measured 9s on the TypeScript corpus) → prune rows for files NOT in the current set → meta upsert (generation, version, hash_records_complete, index_mode) → COMMIT. Any failure ⇒ ROLLBACK.

### Decisive source
```c
/* Sub-block timings (publish.timing style): coverage_replace measured 9 s on
 * the TypeScript corpus and the caller-level block could not say WHY — delete,
 * 13k row inserts with large error_ranges payloads, the NOT-IN prune, meta,
 * and COMMIT are very different suspects. */
struct timespec cov_t0; ... long cov_ms[5] = {0,0,0,0,0};
```

**Flow:** BEGIN → wipe project rows → batched prepared inserts (skipping rows lacking path/kind) → prune orphans against the fresh manifest → write meta → COMMIT; every early exit rolls back; timings recorded per sub-block.
**Invariant:** The whole replace is atomic — partial coverage sets must never be visible; the prune step keeps rows consistent when file discovery shrinks between runs.
**Probe:** consumers in tests/test_mcp.c:2577–2850 (`tool_check_index_coverage_finds_path_beyond_status_cap` seeds 502 rows through this path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_coverage_replace", limit: 5 });
```

## Verdict
Adopt transactional replace + sub-block timing ledgers for bulk metadata rewrites; adapt row schema; the "which suspect" comment discipline is worth copying verbatim.
