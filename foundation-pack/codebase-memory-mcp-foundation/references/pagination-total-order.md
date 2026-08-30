<!-- capsule-v2 -->
# Search pagination stability — why does ORDER BY need a tie-breaker before you add LIMIT/OFFSET?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you guarantee contractually stable pages when names are non-unique?

## (name, id) unique total order
**Path/Symbol:** `src/store/store.c:cbm_store_search` ORDER BY construction (4468–4478).
**Signature:** embedded in `int cbm_store_search(cbm_store_t *s, const cbm_search_params_t *params, cbm_search_output_t *out);`
**Data Shape:** `ORDER BY <name_col>, <id_col> LIMIT ? OFFSET ?` — column qualifiers switch between `n.name/n.id` and bare `name/id` depending on whether the degree-filter wrapped the query in a subquery. Count query strips per-row edge subqueries unless degree filters reference them.

### Decisive source
```c
/* (name, id) is a unique total order — names are non-unique, and without
 * the tie-break offset pages are not contractually stable across calls. */
snprintf(order_limit, sizeof(order_limit), " ORDER BY %s, %s LIMIT %d OFFSET %d", name_col,
         id_col, limit, offset);
```

**Flow:** build SELECT with correlated in/out degree subqueries → apply degree filter (may wrap as derived table, changing column qualification) → count via stripped query for the common case → page rows under the total order.
**Invariant:** Every paginated endpoint must sort by a UNIQUE key as final tiebreaker; qualifier switching must track any subquery wrapping or the SQL breaks.
**Probe:** `tests/test_store_search.c:store_search_degree_filter`, `store_search_degree_counts_inherits`, plus trace-level pagination exactly-once in tests/test_mcp.c:3101.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_search", limit: 5 });
```

## Verdict
Adopt unique-tiebreak ordering and count-query stripping; adapt to your ORM/query builder; nothing exotic to omit.
