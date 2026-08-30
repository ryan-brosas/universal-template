<!-- capsule-v2 -->
# Multi-type BFS — how do you traverse CALLS and HTTP_CALLS together with depth limits?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the BFS API surface (direction, edge types, depth, max nodes) and its result contract?

## Direction + type-array + depth/max-bounded traversal
**Path/Symbol:** `src/store/store.c:cbm_store_bfs` (4676+) + tests/test_store_search.c:448 (`store_bfs_outbound`), 493 (`store_bfs_inbound`), 718 (`store_bfs_cross_service`), 762 (`store_bfs_depth_chain`).
**Signature:** `int cbm_store_bfs(cbm_store_t *s, int64_t start_id, const char *direction, const char **edge_types, int type_count, int max_depth, int max_nodes, cbm_traverse_result_t *out);`
**Data Shape:** Direction ∈ {outbound, inbound}; edge_types array selects which relations to follow; result = visited[] nodes + traversed edges[] with types; free via cbm_store_traverse_free.

### Decisive source
```c
/* BFS from A with both CALLS and HTTP_CALLS */
const char *types[] = {"CALLS", "HTTP_CALLS"};
cbm_traverse_result_t result = {0};
int rc = cbm_store_bfs(s, idA, "outbound", types, 2, 1, 200, &result);
ASSERT_EQ(rc, CBM_STORE_OK);
ASSERT_GTE(result.visited_count, 1); /* B */
```

**Flow:** seed frontier → per level: SELECT neighbors by direction+types → dedup via visited set → record the EDGE that reached each node → stop at depth or node budget → return.
**Invariant:** Edge provenance must be preserved (which edge reached which node) for impact explanations; budgets are hard caps, not soft hints.
**Probe:** the four BFS tests plus `store_hop_to_risk`/`store_build_impact_summary` consumers at 851/863.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_bfs", limit: 5 });
```

## Verdict
Adopt typed multi-relation BFS with explicit budgets; adapt defaults; keep edge-provenance in results.
