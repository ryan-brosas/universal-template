<!-- capsule-v2 -->
# Search primitives — fulltext, similarity, BFS per node/edge/episode/community

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does a graph memory offer one search primitive per (entity kind × query mode), portable across four graph DBs?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/search/search_utils.py` (2,048 lines): `fulltext_query` (:85), `edge_fulltext_search` (:185), `edge_similarity_search` (:291-438), `edge_bfs_search` (:439), `node_fulltext_search` (:563), `node_similarity_search` (:656), `node_bfs_search` (:774), `episode_fulltext_search` (:870), `community_fulltext_search` (:956), `community_similarity_search` (:1045); filters in `search/search_filters.py` (`SearchFilters`, `edge_search_filter_query_constructor`); entrypoints `search/search.py`: `search` (:98), `edge_search` (:253), `node_search` (:463), `episode_search` (:663), `community_search` (:763).
**Signature:** `edge_similarity_search(driver, search_vector, source_node_uuid?, target_node_uuid?, search_filter, group_ids?, limit, min_score)` — vector search over RELATES_TO fact edges; `node_bfs_search` — breadth-first from origin nodes; each primitive delegates to `driver.search_interface` first, falling back to generic Cypher.
**Data Shape:** `SearchFilters` (node/edge attribute filters) → `(filter_queries, filter_params)` via the constructor; group_ids scoping appended as `IN $group_ids`; Kuzu needs an intermediate `RelatesToNode_` hop; Neptune gets its own query shape.

### Decisive source
```ts
async def edge_similarity_search(driver, search_vector, source_uuid, target_uuid, search_filter, ...):
    if driver.search_interface:                      # provider fast-path first
        return await driver.search_interface.edge_similarity_search(...)
    match_query = "MATCH (n:Entity)-[e:RELATES_TO]->(m:Entity)"
    if driver.provider == GraphProvider.KUZU:        # per-provider dialect
        match_query = "MATCH (n:Entity)-[:RELATES_TO]->(e:RelatesToNode_)-[:RELATES_TO]->(m:Entity)"
    filter_queries, filter_params = edge_search_filter_query_constructor(search_filter, driver.provider)
    if group_ids is not None:
        filter_queries.append('e.group_id IN $group_ids')
    # cosine similarity over e.fact_embedding, ORDER BY score LIMIT $limit
```

**Flow:** every primitive follows one shape — provider interface fast-path → generic Cypher fallback → per-provider dialect fixes (Kuzu hop, Neptune form) → filter construction from `SearchFilters` → group scoping → similarity/fulltext/BFS execution with limit + min_score. The five top-level entrypoints compose these primitives into named recipes.
**Invariant:** provider quirks live inside the primitives, never in callers; filters are declarative (`SearchFilters`) and translated once; every search is bounded (limit + min_score).
**Probe:** `tests/` search tests (similarity search returns fact edges ordered by cosine; fulltext respects include list; BFS walks from origin; filters narrow results).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "edge_similarity_search node_bfs_search fulltext SearchFilters search recipe", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the primitive matrix (kind × mode: fulltext/similarity/BFS) behind a provider interface + generic-Cypher fallback; adapt the dialect fixes and filter vocabulary to host.
