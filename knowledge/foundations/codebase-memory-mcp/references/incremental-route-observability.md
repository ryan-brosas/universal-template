<!-- capsule-v2 -->
# Incremental route observability — how do you TEST which incremental strategy ran without exposing test hooks in prod?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you assert NOOP vs CLOSURE_REPAIR vs FORCED_FULL routing in tests while keeping production binaries clean?

## Compile-time-gated last-route atomic
**Path/Symbol:** `src/pipeline/pipeline_incremental.c:52–69` (`g_incr_test_last_route`, `incr_test_set_last_route`) + consumers tests/test_pipeline.c:2168–2185.
**Signature:** `static void incr_test_set_last_route(cbm_incremental_route_t r);` / `cbm_incremental_route_t cbm_pipeline_incremental_test_last_route(void);` — all inside `#if defined(CBM_INCREMENTAL_TEST_API)`.
**Data Shape:** Routes: NONE (reset), NOOP, FORCED_FULL, CLOSURE_REPAIR, LEGACY_PARTIAL (test-only path). Production build: zero code, zero storage.

### Decisive source
```c
#if defined(CBM_INCREMENTAL_TEST_API) && CBM_INCREMENTAL_TEST_API
static atomic_int g_incr_test_last_route = CBM_INCREMENTAL_ROUTE_NONE;
...
#endif
...
/* test side */
cbm_pipeline_incremental_test_reset_faults();
ASSERT_EQ(cbm_pipeline_incremental_test_last_route(), CBM_INCREMENTAL_ROUTE_NOOP);
```

**Flow:** every routing branch stores its decision into the atomic (test builds only) → tests reset faults, run a scenario, then assert the exact route → production compiles the branches WITHOUT the store, so the same code paths execute with no observability overhead or attack surface.
**Invariant:** Test seams are OPT-IN at compile time — the failure mode of forgetting the flag is a clean binary; never gate behavior (only observation) on the seam.
**Probe:** `tests/test_pipeline.c:pipeline_closure_repair_body_edit_converges_with_fresh_full` (route == CLOSURE_REPAIR), `tests/test_incremental.c:incr_noop_reindex`; Makefile wires `-DCBM_INCREMENTAL_TEST_API=1` only into CFLAGS_TEST.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "incr_test_set_last_route", limit: 5 });
```

## Verdict
Adopt compile-time seam atoms for behavioral observability in tests; adapt route enum; the opt-in-not-opt-out rule is the transferable part.
