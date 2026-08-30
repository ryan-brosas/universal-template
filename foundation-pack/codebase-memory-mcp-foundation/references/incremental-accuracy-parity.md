<!-- capsule-v2 -->
# Incremental accuracy parity — what test proves a partial reindex equals a full one?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you pin "incremental ≈ full" without flaky exact counts?

## Bounded-delta node/edge comparison after forced full
**Path/Symbol:** `tests/test_incremental.c:incr_accuracy_vs_full` (862–900).
**Signature:** harness helpers `index_repo()`, `get_node_count()`, `get_edge_count_by_type("CALLS")`.
**Data Shape:** Tolerance: |full_nodes − incr_nodes| ≤ 2 (dedup timing), CALLS edges ≤ 2; the second bound (≤50) is legacy slack kept only as an upper sanity rail.

### Decisive source
```c
/* Delete DB, force full reindex */
unlink(g_dbpath);
resp = index_repo();
...
/* Within tight tolerance (±2 for dedup timing differences) */
ASSERT_LTE(abs(full_nodes - incr_nodes), 2);
ASSERT_LTE(abs(full_calls - incr_calls), 2);
```

**Flow:** index incrementally → capture node/edge/CALLS totals → delete the DB → full reindex → re-capture → assert per-class deltas within ±2. Complemented by route assertions (`CBM_INCREMENTAL_ROUTE_NOOP` on unchanged tree, `CLOSURE_REPAIR` on body edit, `FORCED_FULL` on added defs) via the CBM_INCREMENTAL_TEST_API.
**Invariant:** Parity claims must be per-edge-type and tolerance-bounded — exact equality is impossible while parallel LSH/resolve dedups race; a missing route assertion lets silent full-rebuild regressions hide behind "still correct".
**Probe:** `tests/test_incremental.c:incr_accuracy_vs_full`, `incr_noop_reindex`; planner-side in `tests/test_pipeline.c:pipeline_closure_repair_*` family.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "incr_accuracy_vs_full", limit: 5 });
```

## Verdict
Adopt type-scoped bounded-parity plus explicit route assertions for incremental systems; adapt tolerances to your nondeterminism budget; omit perf probes from gating (they warn, not fail).
