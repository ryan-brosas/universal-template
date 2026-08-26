<!-- capsule-v2 -->
# Degree-filter SQL — how do you filter nodes by fan-in/fan-out without correlated-subquery explosions?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the pattern for "min_in_degree=3 AND max_out_degree=1" over an edges table?

## Derived-table wrap with stripped count query
**Path/Symbol:** `src/store/store.c:cbm_store_search` degree arm (4478–4520).
**Signature:** embedded in `int cbm_store_search(cbm_store_t *s, const cbm_search_params_t *params, cbm_search_output_t *out);`
**Data Shape:** When any degree bound set: base SELECT wrapped as derived table computing in_deg/out_deg via scalar subqueries per row → HAVING-style WHERE on the wrapper; COUNT query strips per-row edge subqueries unless degree filters reference them (correctness over speed).

### Decisive source
```c
/* Degree filters: wrap the base query so each row carries its computed
 * degrees, then filter on them. The count query keeps subqueries ONLY when
 * a degree bound references them — otherwise it strips for speed. */
```

**Flow:** detect degree params → build inner select with `(SELECT COUNT(*) FROM edges e WHERE e.target_id=n.id AND e.type='CALLS') AS in_deg` etc. → outer WHERE applies bounds → pagination ORDER stays unique (see pagination capsule) → count path mirrors structure conditionally.
**Invariant:** Count-query stripping must be conditional on the SAME predicate that adds the columns; unconditional stripping breaks totals under degree filters.
**Probe:** `tests/test_store_search.c:store_search_degree_filter`, `store_search_degree_counts_inherits`, `store_search_isolated_node_zero_degree`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "degree", limit: 5 });
```

## Verdict
Adopt conditional-structure mirroring between page and count queries; adapt to your query builder; pin zero-degree semantics explicitly.
