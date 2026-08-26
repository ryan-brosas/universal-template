<!-- capsule-v2 -->
# Edge cross-encoder shortlist — which candidates reach CE ranking without BM25 insertion-order bias?

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `graphiti`. **Question:** when the edge reranker is `cross_encoder`, what exactly gets sent to the encoder, and why did the pre-fix code systematically starve cosine/BFS hits (#1642)?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/search/search.py`: `edge_search` (:253-461), `cross_encoder` branch (:396-410); fusion primitive `rrf` in `graphiti_core/search/search_utils.py:1764-1779`.
**Signature:** inside `edge_search(..., config: EdgeSearchConfig, ..., limit: int)`:
```py
search_result_uuids = [[edge.uuid for edge in result] for result in search_results]
rrf_result_uuids, _ = rrf(search_result_uuids, min_score=reranker_min_score)
rrf_edges = [edge_uuid_map[uuid] for uuid in rrf_result_uuids][: 2 * limit]
fact_to_uuid_map = {edge.fact: edge.uuid for edge in rrf_edges}
```
**Data Shape:** `search_results: list[list[EntityEdge]]` — one ranked list per configured method (bm25/cosine/bfs each already fetched at `2 * limit`); optional late BFS expansion appends one more list before the map is built; `edge_uuid_map: dict[uuid → EntityEdge]` dedupes across methods; `fact_to_uuid_map: dict[fact → uuid]` keys CE passages back to edges; branch returns `(reranked_edges[:limit], edge_scores[:limit])`.

### Decisive source
```python
# BEFORE (starved cosine/BFS): first `limit` values of the DEDUPED dict in
# insertion order — which equals BM25's order whenever BM25 ran.
fact_to_uuid_map = {e.fact: e.uuid for e in list(edge_uuid_map.values())[:limit]}

# AFTER: fuse per-method rank lists FIRST (RRF), then cap the shortlist.
search_result_uuids = [[edge.uuid for edge in result] for result in search_results]
rrf_result_uuids, _ = rrf(search_result_uuids, min_score=reranker_min_score)
rrf_edges = [edge_uuid_map[uuid] for uuid in rrf_result_uuids][: 2 * limit]
fact_to_uuid_map = {edge.fact: edge.uuid for edge in rrf_edges}
```

**Flow:** methods run concurrently (`semaphore_gather`) → BFS expansion may append a list → uuid lists fused by `rrf` (score += `1/(i+rank_const)` per list position, stable sort desc, `min_score` filter) → slice `2 * limit` → CE `rank(query, facts)` → `score >= reranker_min_score` filter → top `limit`.
**Invariant:** the CE budget is exactly `min(|fused|, 2 * limit)` — never unbounded, never bare `limit`. RRF tie structure is load-bearing: a method's rank-1 scores 1.0, which nothing exceeds, so it sits within the first `(#methods)` fused positions and always survives the `2 * limit` cut; Python's stable sort breaks head-ties by list order, not method priority. A porter who reverts to "first N of the dedup map" reintroduces #1642: dict insertion order = BM25's fetch order crowds out cosine/BFS candidates entirely. Note the scale trap: the SAME `reranker_min_score` filters RRF fractions (~1.0 down to ~1/(2·limit)) pre-slice AND CE scores post-rank — keep it near 0 or fusion silently empties.
**Probe:** `tests/utils/search/test_edge_cross_encoder_rrf_shortlist.py:25` (`test_rrf_shortlist_includes_cosine_top_hit` — asserts `len(ranked_passages) == 2 * limit` and cosine winner first) and `:71` (`test_smoke_alice_works_at_zep_reaches_cross_encoder` — BM25 fills weak hits, cosine carries the answer, Zep fact must appear in CE passages). EXECUTED under repo `.venv`: 2 passed at `993e081a`; RED (both fail) with the two pre-fix files checked out from `401c59a6`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "edge_search", limit: 10, fields: ["signature", "name", "file"] });
// → graphiti_core/search/search.py edge_search :253-461 (branch at :396-410)
// NOTE: repo moved behind a symlink (inspo/graphiti → inspo/memory/graphiti); the
// path-slugged twin above serves the FRESH @993e081a graph. Short-name "graphiti"
// is STUCK pre-drift (@401c59a) — refresh-in-place through it is impossible.
```

## Verdict
Adopt RRF-fuse-before-rank with a `2 * limit` CE candidate cap plus the tie-position argument for why every method's best survives; adapt the cap constant and method roster to your search families; omit graphiti's tracing phases (`_trace_phase`) if you have no span plane. Coverage caveat: none — direct upstream tests pin both polarities and were executed live.
