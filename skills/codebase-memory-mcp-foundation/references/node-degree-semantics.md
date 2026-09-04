<!-- capsule-v2 -->
# Node degree queries — how do you get a node's fan-in/fan-out in one call?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the degree API and its per-type semantics?

## COUNT over inbound/outbound with type filter
**Path/Symbol:** `src/store/store.c:cbm_store_node_degree` + tests/test_store_nodes.c:957 (`store_node_degree`).
**Signature:** `int cbm_store_node_degree(cbm_store_t *s, int64_t node_id, const char *type, bool inbound, int *out);`
**Data Shape:** Counts edges touching node_id; NULL type = all types (CALLS and INHERITS must not double-count a single edge — see store_search_degree_calls_plus_inherits_no_double_count); direction flag selects source/target side.

### Decisive source
```c
TEST(store_node_degree) { ... }
TEST(store_search_degree_calls_plus_inherits_no_double_count) { ... }
```

**Flow:** prepared COUNT with bound id + optional type → return scalar.
**Invariant:** Multi-type degree sums DISTINCT EDGES, not per-type counts added naively (an edge has exactly one type so per-type sums happen to be safe here — but search-side multi-type filters pin the semantics explicitly).
**Probe:** `tests/test_store_nodes.c:store_node_degree` plus search-side degree family.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_node_degree", limit: 5 });
```

## Verdict
Adopt single-edge-count semantics for degree APIs; adapt type filters; keep hotspots/impact consistent with these numbers.
