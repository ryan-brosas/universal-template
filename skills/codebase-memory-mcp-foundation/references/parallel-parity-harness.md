<!-- capsule-v2 -->
# Parallel parity harness — how do you prove a parallel pipeline extracts exactly what the sequential one does?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What fixture-and-assert shape catches worker-scheduling divergences in edge production?

## Same repo through both engines, per-edge-type count equality
**Path/Symbol:** `tests/test_parallel.c:assert_edge_type_parity` (431–441) + sequential-with-LSP-cross helper (~197–210).
**Signature:** `static int assert_edge_type_parity(const char *type);` comparing `cbm_gbuf_edge_count_by_type(g_seq_gbuf, type)` vs `g_par_gbuf`.
**Data Shape:** Fixture: multi-file Go/TS project (`main.go`, `pkg/service.go`, …) indexed once via `cbm_pipeline_pass_definitions/calls/usages/semantic` sequentially and once via the parallel pool; equality asserted per type: CALLS, DEFINES, DEFINES_METHOD, IMPORTS, USAGE, INHERITS, …

### Decisive source
```c
static int assert_edge_type_parity(const char *type) {
    if (ensure_parity_setup() != 0) return -1;
    int seq = cbm_gbuf_edge_count_by_type(g_seq_gbuf, type);
    int par = cbm_gbuf_edge_count_by_type(g_par_gbuf, type);
    if (seq != par) { printf("  FAIL: %s edges: seq=%d par=%d\n", type, seq, par); return 1; }
```
```c
/* Production's sequential pipeline retains one extraction cache and runs the
 * cross-file LSP pass between definitions and edge materialization. */
```

**Flow:** build fixture → run sequential engine into one graph buffer → run parallel engine into another → compare counts per edge type → any mismatch names the type and both counts. Complements semantic-level pins like `usage_semantic_reference_candidate_trusts_marked_producer`.
**Invariant:** Parity must hold PER TYPE (aggregate totals can mask offsetting errors); both engines must share the same extraction-cache/LSP-pass ordering assumptions or the test lies.
**Probe:** `tests/test_parallel.c:parallel_calls_parity`, `parallel_defines_parity`, `parallel_imports_parity`, `parallel_usage_parity`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_parallel_for", limit: 5 });
```

## Verdict
Adopt dual-engine parity suites for any parallelization of deterministic extraction; adapt the type list; keep the shared-cache ordering note — it is where divergence usually hides.
