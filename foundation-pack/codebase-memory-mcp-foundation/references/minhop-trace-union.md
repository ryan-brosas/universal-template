<!-- capsule-v2 -->
# Multi-seed trace union — how do you trace from ambiguous same-name definitions without double-counting hops?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** When a name resolves to a real def AND a stub, what must the union traversal guarantee?

## BFS union with min-hop recording across seeds
**Path/Symbol:** `src/mcp/mcp.c` trace union + tests/test_mcp.c:3025 (`tool_trace_union_records_min_hop_across_seeds`), 3503 (`distinct_defs_not_over_unioned`), 3573 (`dts_stub_unions_with_impl`).
**Signature:** trace_path over multiple resolved seeds; per-node hop = MIN across seeds.
**Data Shape:** Fixture: seed A (real def, a.c) reaches tgt via mid (hop 2); stub seed B (b.d.ts, start==end) reaches tgt directly (hop 1). Union reports tgt at hop 1. pick_resolved_node still picks the REAL definition unambiguously while bfs_union_same_name traverses BOTH.

### Decisive source
```c
/* Seed A (real def, lower id, traversed first) reaches tgt only via mid
 * (hop 2); the stub seed B reaches tgt directly (hop 1). */
```

**Flow:** resolve name → seed set = distinct defs (+stubs for union only) → BFS from all seeds simultaneously → keep minimum hop per node → prefer-definition logic for primary answer.
**Invariant:** Hop distances must aggregate as MIN, not first-write-wins — seed order would otherwise make results depend on rowid ordering.
**Probe:** `tests/test_mcp.c:tool_trace_union_records_min_hop_across_seeds`, `tool_trace_call_path_distinct_defs_not_over_unioned`, `tool_trace_call_path_dts_stub_unions_with_impl`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "trace_union", limit: 5 });
```

## Verdict
Adopt multi-source BFS with min-aggregation for ambiguous symbols; adapt stub handling (.d.ts twins are common); separate "answer node" from "traversal seeds".
