<!-- capsule-v2 -->
# n_hop_with_weight cross-layer contract — how do write-side graph walks survive the round trip to query-side ranking without dying on column defaults?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** What exact structure must an entity chunk carry for n-hop enrichment, and what does a porter need to know about backends that return empty-string columns?

## One JSON field, three defenses
**Path/Symbol:** Write: `rag/graphrag/utils.py:803-824` (`n_neighbor`), `graph_node_to_chunk` (serializes to `n_hop_with_weight`, pagerank to `rank_flt`). Read: `rag/graphrag/search.py:68-94` (`KGSearch._ent_info_from_`). Go twin decode: `internal/service/graph/search.go` `NhopEntityNames`.
**Signature:** `def n_neighbor(graph: nx.Graph, node, n_hop: int = 2) -> list[dict]`; each dict `{"path": (n0, n1, ...), "weights": [w0, w1, ...]}` with `len(weights) == len(path) - 1`.
**Data Shape:** Entity chunk fields consumed by ranking: `entity_kwd` (str or 1-element list), `rank_flt` (float pagerank; relations instead carry `weight_int` int-typed), `content_with_weight` (JSON description), `n_hop_with_weight` (JSON array of path/weights). Go `NhopEntityNames` dedups names across paths and returns nil on invalid JSON.

### Decisive source
```python
# search.py:78-87 — read side defends against absent AND empty-string columns
if isinstance(ent["entity_kwd"], list):
    ent["entity_kwd"] = ent["entity_kwd"][0]
# n_hop_with_weight may be absent (older chunks) or an empty string
# (the Infinity column default), neither of which json.loads handles.
n_hop_raw = ent.get("n_hop_with_weight") or "[]"
try:
    n_hop_ents = json.loads(n_hop_raw)
except (json.JSONDecodeError, TypeError):
    logging.warning(...)
    n_hop_ents = []
```
```python
# utils.py:812-824 + tests — walk is direction-agnostic over undirected edges
source_edge = list(graph.edges(node))
...
wts = nx.get_edge_attributes(graph, "weight")
```
```go
// search.go ParseRelationChunks — int-typed relation pagerank decodes both ways
if v, ok := chunk["weight_int"].(float64); ok { r.PageRank = v }
else if v, ok := chunk["weight_int"].(int); ok { r.PageRank = float64(v) }
```

**Flow:** at indexing time `set_graph` computes `n_neighbor(graph, node)` per changed node and stores it JSON-encoded alongside pagerank; at query time `_ent_info_from_` decodes it defensively, and `KGSearch.retrieval` folds each stored path into n-hop edge credit (`sim/(2+i)` per hop, max-pagerank along the path). The regression class docstring in the test file states the stakes plainly: without `rank_flt` and `n_hop_with_weight`, "KGSearch's pagerank * sim ranking and n-hop enrichment are permanently dead."
**Invariant:** Missing weight attribute defaults to 0; traversal direction never changes the recovered weight (undirected edge attrs may be keyed either way); malformed/absent/empty-string payloads degrade to empty enrichment with a warning — never an exception in the retrieval hot path.
**Probe:** ACTIVE direct tests `test/unit_test/rag/graphrag/test_graphrag_utils.py::TestNNeighbor` (6 tests @p1: isolated node → [], result shape, two-hop weights [1,2], one-hop only, missing-weight→0, direction-agnostic lookup) and `::TestGraphNodeToChunk` (4 tests @p1: `rank_flt` from pagerank meta, defaults 0.0, `n_hop_with_weight` round-trips as JSON list-of-dicts, defaults `"[]"`). Go twin: `TestNhopEntityNames_ValidJSON/Dedup/InvalidJSON`.

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", filePattern: "*graphrag/utils.py", query: "get_graph set_graph embedding vector store graph nodes edges pagerank n_hop", fields: ["lines"] });
await mcp.codebase_memory.get_code_snippet({ project: "ragflow", qualified_name: "ragflow.rag.graphrag.search.KGSearch.retrieval" }); // n-hop fold :171-186
```
Direct reads: `rag/graphrag/utils.py` :803-824; `test/unit_test/rag/graphrag/test_graphrag_utils.py` :519-618; `internal/service/graph/search_test.go` :298-321.

## Verdict
Adopt storing precomputed ≤2-hop paths+weights ON the entity row (query time stays O(hits × paths) with no graph joins) and the triple defense (absent / empty-string / malformed → []). Adapt hop depth, decay divisor, and column typing to your store — but keep entity-pagerank (float) and relation-weight (int-typed column, dual-decoded) distinct as upstream does.
