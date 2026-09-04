<!-- capsule-v2 -->
# Entry-point exclusion predicate — how do you filter "boring roots" out of architecture views without losing dead code?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What SQL shape excludes nodes with inbound CALLS but keeps zero-degree dead code visible?

## NOT(no-inbound AND has-outbound) double-negation
**Path/Symbol:** `src/store/store.c:search_where_advanced` entry-point arm (4392–4400).
**Signature:** embedded in `cbm_store_search` when `params->exclude_entry_points` is set.
**Data Shape:** Predicate: `NOT (NOT EXISTS(inbound CALLS) AND EXISTS(outbound CALLS))` — i.e., drop only true entry points; degree-0 dead code (no calls either way) SURVIVES the filter.

### Decisive source
```c
if (params->exclude_entry_points) {
    /* Exclude nodes with no inbound CALLS but at least one outbound CALLS.
     * Dead code (degree=0) is NOT excluded — only true entry points. */
    *wlen = where_append(where, where_sz, wlen, nparams,
        "NOT (NOT EXISTS(SELECT 1 FROM edges e WHERE e.target_id = n.id "
        "AND e.type = 'CALLS') "
        "AND EXISTS(SELECT 1 FROM edges e2 WHERE e2.source_id = n.id "
        "AND e2.type = 'CALLS'))");
}
```

**Flow:** search builds advanced WHERE arms → this arm appends unbound SQL (constants only, no injection surface) → planner uses CALLS-edge indexes for the two EXISTS probes.
**Invariant:** The double negative is the spec: exclude ONLY (in-degree 0 ∧ out-degree ≥1); rewriting it as `in_degree > 0 OR out_degree = 0` must remain equivalent — tests pin both readings.
**Probe:** degree-filter family in tests/test_store_search.c:237–430 (`store_search_degree_filter`, `store_search_isolated_node_zero_degree`) pins the degree semantics this predicate builds on.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "exclude_entry_points", limit: 5 });
```

## Verdict
Adopt precise set definitions over intuitive ones in graph filters; adapt edge-type names; document WHY dead code survives or someone will "fix" it into invisibility.
