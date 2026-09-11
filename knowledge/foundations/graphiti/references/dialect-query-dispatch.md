<!-- capsule-v2 -->
# Provider dialect dispatch — one index name, four query grammars

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** how does one logical fulltext/vector index name (e.g. `node_name_and_summary`) compile to four different databases' syntax without leaking dialect into callers?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/graph_queries.py:get_fulltext_indices` (:85–140), `get_nodes_query` (:143–152), `get_vector_cosine_func_query` (:155–163), `get_relationships_query` (:166–175), `get_range_indices` (:28–82); label maps `NEO4J_TO_FALKORDB_MAPPING` / `INDEX_TO_LABEL_KUZU_MAPPING` (:13–25).
**Signature:** `get_nodes_query(name: str, query: str, limit: int, provider: GraphProvider) -> str`; `get_vector_cosine_func_query(vec1, vec2, provider) -> str`.
**Data Shape:** inputs are the *logical* index name (`episode_content`, `node_name_and_summary`, `community_name`, `edge_name_and_fact`) + literal query text; output is a raw query string (params passed separately as `$query`/`$limit`). All strings are typed `LiteralString` to satisfy driver injection linters.

### Decisive source
```python
# The cosine trap: FalkorDB exposes DISTANCE, not similarity.
if provider == GraphProvider.FALKORDB:
    # FalkorDB uses a different syntax for regular cosine similarity and
    # Neo4j uses normalized cosine similarity
    return f'(2 - vec.cosineDistance({vec1}, vecf32({vec2})))/2'
if provider == GraphProvider.KUZU:
    return f'array_cosine_similarity({vec1}, {vec2})'   # already a similarity
return f'vector.similarity.cosine({vec1}, {vec2})'       # Neo4j
```

**Flow:** caller holds a logical name → provider switch selects grammar: FalkorDB `CALL db.idx.fulltext.queryNodes('<Label>', …)` with a *label* looked up from the Neo4j-name map; Kuzu `CALL QUERY_FTS_INDEX('<Label>', '<name>', $query, TOP := $limit)`; Neo4j `CALL db.index.fulltext.queryNodes("<name>", $query, {limit: $limit})`. Index DDL differs just as much: Kuzu uses stored procedures `CREATE_FTS_INDEX`, FalkorDB passes its `STOPWORDS` list into `createNodeIndex`, Neo4j declares named indexes `IF NOT EXISTS`.
**Invariant:** (1) higher scores must always mean *more similar* across providers — that is why FalkorDB rescales `(2 − cosineDistance)/2`; using the raw distance as a score inverts every ranking. (2) Kuzu's edge index targets label `RelatesToNode_` (edge-as-node), while FalkorDB/Neo4j use relationship `RELATES_TO` — the maps encode this, never hardcode it. (3) FalkorDB range-index DDL has NO `IF NOT EXISTS` while Neo4j's does — re-running creation is safe only per-dialect.
**Probe:** `tests/utils/search/test_edge_bfs_query_shape.py` pins query-shape per provider; `tests/driver/test_falkordb_ops_routing.py` pins FalkorDB op routing. No unit test asserts the cosine rescale formula itself (coverage caveat — verified by direct source read at :155–163).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "get_vector_cosine_func_query get_nodes_query GraphProvider fulltext indices", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the logical-name→dialect-Grammar dispatch shape and the similarity-normalization invariant (rescale distances); adapt the per-provider SQL/Cypher bodies; omit providers you don't target but keep the mapping table pattern so adding one is a table row, not a grep.
