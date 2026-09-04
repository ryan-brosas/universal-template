<!-- capsule-v2 -->
# BFS shortest-path CTE — how do you traverse a graph stored in SQL without self-loops exploding the result?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What recursive-CTE shape yields each reachable node exactly once at minimal distance with deterministic order?

## UNION dedupe + MIN(hop) GROUP BY
**Path/Symbol:** `src/store/store.c:cbm_store_bfs` (4676–4784).
**Signature:** `int cbm_store_bfs(cbm_store_t *s, int64_t start_id, const char *direction, const char **edge_types, int edge_type_count, int max_depth, int max_results, cbm_traverse_result_t *out);`
**Data Shape:** Direction flips the join predicate (`e.target_id = bfs.node_id` inbound vs source outbound); empty edge_types binds `"CALLS"`; output rows carry `hop` = BFS depth excluding the root.

### Decisive source
```sql
WITH RECURSIVE bfs(node_id, hop) AS (
  SELECT ?1, 0
  UNION                                -- dedupes (node, hop) PAIRS
  SELECT e.<next>, bfs.hop + 1 FROM bfs JOIN edges e ON <join_cond>
  WHERE e.type IN (...) AND bfs.hop < ?
)
SELECT n.*, MIN(bfs.hop) AS hop FROM bfs
JOIN nodes n ON n.id = bfs.node_id
WHERE bfs.hop > 0                     -- exclude root (self via a loop still appears)
GROUP BY n.id
ORDER BY hop, n.id                    -- (hop,id): unique total order → stable pages
LIMIT ?;
```
```c
/* SHORTEST-PATH semantics: the UNION dedupes (node, hop) PAIRS, so a single
 * self-loop minted every hop level for every node it could reach ... (#797). */
```

**Flow:** resolve root node by id → build types clause (bound parameters, never spliced) → run CTE → project nodes at MIN hop → deterministic `(hop, id)` ordering keeps pagination watermarks reproducible.
**Invariant:** Use plain UNION (not UNION ALL) — the pair-dedupe is what bounds a cyclic graph; GROUP BY node with MIN(hop) converts walk-pairs into shortest distances; root excluded even when a loop returns to it.
**Probe:** `tests/test_store_search.c:store_bfs_outbound`, `store_bfs_inbound`, `store_bfs_depth_chain` pin direction/depth semantics end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_bfs", limit: 5 });
```

## Verdict
Adopt the UNION+MIN(hop)+total-order CTE for any SQL-backed traversal; adapt edge-table/column names; omit multi-seed support unless you need impact radius from many roots (`bfs_multi` twin exists).
