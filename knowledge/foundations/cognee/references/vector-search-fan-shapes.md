<!-- capsule-v2 -->
# Vector search fan — per-collection gather with stable empty shapes

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How should one query be searched across many vector collections so missing collections and batch/single modes never corrupt downstream distance mapping?

## NodeEdgeVectorSearch
**Path/Symbol:** `cognee/modules/retrieval/utils/node_edge_vector_search.py:NodeEdgeVectorSearch.embed_and_retrieve_distances` (:36-84), `set_distances_from_results` (:114-143), `_search_single_collection` (:203-221).
**Signature:** `embed_and_retrieve_distances(query=None, query_batch=None, collections, wide_search_limit=None, node_name=None, node_name_filter_operator="OR")` (exactly one of query/query_batch).
**Data Shape:** Edge hits live in the dedicated `EdgeType_relationship_name` collection; `node_distances: dict[str, list]`, `edge_distances: list`; single mode = flat lists, batch = list-of-lists.

### Decisive source
```python
# Missing/empty collections become structurally valid empties — NEVER omitted keys:
if not result:
    empty_result = [] if query_list_length is None else [[] for _ in range(query_list_length)]
    if collection == self.edge_collection:
        self.edge_distances = empty_result
    else:
        self.node_distances[collection] = empty_result

# CollectionNotFoundError ⇒ that collection contributes nothing, no error:
except CollectionNotFoundError:
    return []

# Sync __init__ can't await the async engine factory — lazy resolve documented:
# ``get_vector_engine_async()`` is async, so this sync ``__init__`` can't
# eagerly resolve it. Keep the (possibly-None) injected engine and resolve lazily.
```

**Flow:** validate query xor batch → embed once (`query_vector` stored for neighborhood re-scoring reuse) → gather one search task PER collection (batch mode uses `vector_engine.batch_search`) → split results into node vs edge distances with shape-stable empties → `has_results()` short-circuits triplet ranking when everything was empty.
**Invariant:** (1) Shape discipline is the contract: `map_vector_distances_to_graph_*` normalizes by first-element nesting and RAISES on length mismatch — a silently wrong shape here becomes a confusing failure three layers down. (2) `extract_relevant_node_ids()` returns [] in batch mode (ID-filtered projection is single-query-only). (3) wide_search_limit applies ONLY in single mode; batch always projects from full graph.
**Probe:** `cognee/tests/unit/modules/retrieval/test_node_edge_vector_search.py` (whole file).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "NodeEdgeVectorSearch embed_and_retrieve_distances set_distances_from_results edge_collection", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-collection gather + structural empties + explicit single/batch shapes; adapt collection names to your schema; omit neighborhood re-scoring hooks unless you port k-hop projection.
