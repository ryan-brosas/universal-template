<!-- capsule-v2 -->
# Retrieval-for-update — relevant nodes/edges + invalidation candidates

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** when a new episode arrives, how does the system find the existing nodes/edges the new facts touch, so it can update or invalidate instead of duplicating?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/search/search_utils.py` (2,048 lines): `hybrid_node_search` (:1163), `get_relevant_nodes` (:1237), `get_relevant_edges` (:1391), `get_edge_invalidation_candidates` (:1576-1763); `calculate_cosine_similarity` (:71).
**Signature:** `get_relevant_nodes(driver, embeddings, search_filter, group_ids?, limit)` — hybrid (fulltext+cosine) node retrieval for incoming entities; `get_edge_invalidation_candidates(driver, edges, search_filter, min_score, limit)` — for each new fact-edge, returns lists of existing similar edges (`list[list[EntityEdge]]`) that may need invalidation.
**Data Shape:** per input edge, candidates are edges touching either endpoint (`n.uuid IN [source,target] OR m.uuid IN [...]`), scored by cosine between stored `fact_embedding` and the incoming edge's embedding; results grouped one list per input edge.

### Decisive source
```ts
async def get_edge_invalidation_candidates(driver, edges, search_filter, min_score, limit):
    if len(edges) == 0: return []
    filter_queries, filter_params = edge_search_filter_query_constructor(search_filter, driver.provider)
    # UNWIND $edges AS edge
    # MATCH (n:Entity)-[e:RELATES_TO {group_id: edge.group_id}]->(m:Entity)
    # WHERE n.uuid IN [edge.source_node_uuid, edge.target_node_uuid]
    #    OR m.uuid IN [edge.target_node_uuid, edge.source_node_uuid]
    score = calculate_cosine_similarity(r['source_embedding'], r['target_embedding'])
    if score > min_score: keep {id, score, uuid}
```

**Flow:** on ingestion, extract candidate entities → `get_relevant_nodes` finds existing nodes (hybrid fulltext+vector) → `get_relevant_edges` finds edges between them → `get_edge_invalidation_candidates` finds semantically-similar existing facts per new edge → the resolution layer then decides UPDATE/INVALIDATE vs CREATE.
**Invariant:** invalidation is similarity-driven (cosine > min_score against endpoints' touching edges), not exact-match; empty input short-circuits to `[]`; every query is bounded by limit/min_score.
**Probe:** `tests/` search tests (invalidation candidates returned per input edge; endpoint-touching constraint; cosine threshold respected).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "get_edge_invalidation_candidates get_relevant_nodes get_relevant_edges hybrid_node_search", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the retrieval-for-update pattern (find touching edges by endpoints, rank by cosine, group per input edge) to drive update-vs-create decisions; adapt thresholds and grouping to host.
