<!-- capsule-v2 -->
# Vector search over int8 blobs — how do you do cosine similarity inside SQLite with zero extensions?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How are embeddings stored, scored in-SQL, and re-ranked for multi-keyword queries?

## Scalar UDF + first-keyword prefilter + min-across-keywords rerank
**Path/Symbol:** `src/store/store.c:cbm_store_vector_search` (8565–8665) + `sqlite_cosine_i8` (617–657) + registration at 721/910.
**Signature:** `int cbm_store_vector_search(cbm_store_t *s, const char *project, const char **keywords, int keyword_count, int limit, cbm_vector_result_t **out, int *out_count);`
**Data Shape:** Vectors = int8-quantized BLOBs, fixed dim; UDF returns double in [-1,1] with denominator epsilon 1e-10 and mismatched/empty lengths ⇒ score 0.0. Query: build per-keyword vectors from the token table, ORDER BY cosine against the FIRST keyword DESC LIMIT limit*5, then re-score candidates by MIN across all keywords.

### Decisive source
```c
/* Scan all node vectors, compute per-keyword cosine, take min.
 * We use the FIRST keyword as the SQL sort (for top-K pre-filter),
 * then re-score with min across all keywords in the append helper. */
const char *sql = "SELECT n.id, ..., cbm_cosine_i8(v.vector, ?1) as score, v.vector"
                  " FROM node_vectors v INNER JOIN nodes n ON n.id = v.node_id"
                  " WHERE v.project = ?2 AND n.label IN (" CBM_SQL_CALLABLE_OR_TYPE_LABELS ")"
                  " ORDER BY score DESC LIMIT ?3";
```

**Flow:** resolve keyword → token-vec rows (int8 blob + idf weight) → assemble query vector → SQL top-K via registered DETERMINISTIC function → append helper recomputes exact int32-dot cosines per keyword and keeps the minimum → trim to limit.
**Invariant:** Quantized prefilter scores are advisory; final ranking must use the same UDF math across ALL keywords or ordering flips run-to-run; non-blob inputs degrade to 0.0 rather than erroring.
**Probe:** exercised through MCP search_graph semantic_query paths (`tests/test_mcp.c:tool_search_graph_semantic_only_skips_structural_results_issue1295` pins that semantic-only mode never leaks structural rows); UDF correctness guarded by the store suite's vector tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_store_vector_search", limit: 5 });
```

## Verdict
Adopt in-SQL quantized scoring + two-phase prefilter/rerank when you cannot ship a vector extension; adapt dims to your embedder; omit RaBitQ codes unless recall demands them.
