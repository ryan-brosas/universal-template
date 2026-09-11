<!-- capsule-v2 -->
# Neptune AOSS search fusion — when the graph has no native fulltext/vector index, how do two round trips stay ordered and score-correct?

**Source:** Graphiti Apache-2.0 `main@401c59a` (`graphiti_core/driver/neptune/operations/search_ops.py`); Codebase Memory `graphiti`. **Question:** How does BM25 and semantic retrieval work when AOSS owns text search but the property graph owns the records — without losing ranking or wasting a third round trip?

## Two-phase candidate-then-hydrate with score-carrying ids
**Path/Symbol:** `graphiti_core/driver/neptune/operations/search_ops.py:NeptuneSearchOperations.node_fulltext_search` (:59–96), `node_similarity_search` (:100–165), `community_similarity_search` (:~480–545).
**Signature:** `async node_fulltext_search(self, executor: QueryExecutor, query: str, search_filter: SearchFilters, group_ids: list[str] | None = None, limit: int = 10) -> list[EntityNode]`.
**Data Shape:** phase 1 yields `input_ids: list[{'id': str|int, 'score': float}]`; phase 2 is one `UNWIND $ids` Cypher hydration query. Similarity vectors are stored as comma-joined strings in `n.name_embedding`.

### Decisive source
```python
res = driver.run_aoss_query('node_name_and_summary', query, limit=limit)
if not res or res.get('hits', {}).get('total', {}).get('value', 0) == 0:
    return []

input_ids = []
for r in res['hits']['hits']:
    input_ids.append({'id': r['_source']['uuid'], 'score': r['_score']})

cypher = (
    """
    UNWIND $ids as i
    MATCH (n:Entity)
    WHERE n.uuid=i.id
    RETURN
    """
    + get_entity_node_return_query(GraphProvider.NEPTUNE)
    + """
    ORDER BY i.score DESC
    LIMIT $limit
    """
)
records, _, _ = await executor.execute_query(cypher, ids=input_ids, limit=limit)
```
and the similarity twin:
```python
# Neptune: fetch all embeddings, compute cosine in Python
query = ('MATCH (n:Entity)' + filter_query
         + "\n RETURN DISTINCT id(n) as id, n.name_embedding as embedding\n")
...
score = calculate_cosine_similarity(search_vector, list(map(float, r['embedding'].split(','))))
if score > min_score:
    input_ids.append({'id': r['id'], 'score': score})
...
WHERE id(n)=i.id ... ORDER BY i.score DESC LIMIT $limit
```

**Flow:** FULLTEXT — AOSS `multi_match` → zero-hit guard reads `hits.total.value` (missing keys tolerated via chained `.get`) → build `{id: _source.uuid, score: _score}` rows → hydrate in the graph with `UNWIND`, ordering BY the carried score, limiting again in Cypher. SIMILARITY — pull every candidate embedding (comma-string → `list(map(float, split(',')))`), compute cosine in Python, apply `min_score` (default 0.6) BEFORE hydration, skip null embeddings with `if r['embedding']:`, then hydrate survivors keyed on internal `id(n)` (not uuid) with the identical `ORDER BY i.score DESC` shape.
**Invariant:** ordering authority is the carried score, enforced inside phase-2 Cypher (`ORDER BY i.score DESC`) — hydration must never re-sort, dedupe, or truncate ahead of that clause; `min_score` filtering always precedes hydration so the second round trip is bounded. Community search uses the same skeleton with `COMMUNITY_NODE_RETURN_NEPTUNE`.
**Probe:** `tests/utils/search/test_edge_bfs_query_shape.py::test_neptune_generic_edge_searches_return_reference_time` (:103) and `::test_neptune_operations_bfs_search_returns_reference_time` (:125, drives `NeptuneSearchOperations` directly via `RecordingNeptuneDriver`); `tests/test_edge_db_queries.py::test_neptune_uses_start_end_node_with_split_episodes` (:31) pins the Neptune episode-edge query shape. These pin query TEXT shapes, not live AOSS behavior — live-store caveat applies.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "node_fulltext_search NeptuneSearchOperations UNWIND", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the candidate-then-hydrate pattern whenever retrieval lives in a sidecar index: ids travel with scores, hydration preserves external ranking, threshold filters run pre-hydration. Adapt the embedding storage (comma-string is a Neptune openCypher limitation — use native vector types where available). Omit the fetch-ALL-embeddings similarity scan for large graphs — it is O(graph) per query and acceptable only because Graphiti entity counts per group are small.
