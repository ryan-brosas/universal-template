<!-- capsule-v2 -->
# set_graph build-before-delete — in what order must graph persistence run so a crash never destroys the resumable state?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** How is a merged knowledge graph (plus its per-doc subgraphs and embedding chunks) swapped into the store without ever leaving the pipeline unresumable?

## Build everything, then delete, then insert
**Path/Symbol:** `rag/graphrag/utils.py:550-755` (`set_graph`); read path `get_graph` (:530-547), `does_graph_contains` (:502-515).
**Signature:** `async def set_graph(tenant_id: str, kb_id: str, embd_mdl, graph: nx.Graph, change: GraphChange, callback)`.
**Data Shape:** Store rows keyed by `knowledge_graph_kwd`: `"graph"` (whole-graph node-link JSON + source_id list), `"subgraph"` (one per source doc), `"entity"` (name/type/description/`rank_flt`/`n_hop_with_weight`/`q_{dim}_vec`), `"relation"` (sorted pair/weight_int/description/vector). `GraphChange` carries `added_updated_nodes`, `added_updated_edges`, `removed_nodes`, `removed_edges`.

### Decisive source
```python
# utils.py:560-563 + 703-706 — ordering invariant stated in comments
# Build all new chunks first ... before deleting anything.  This ensures that if
# embedding generation or any other step crashes, the old graph and per-doc
# subgraph checkpoints remain intact so the pipeline can resume without re-running.
chunks = [{ "knowledge_graph_kwd": "graph", ... }]           # snapshot first
for source in graph.graph["source_id"]:                      # regenerated subgraphs
    subgraph = graph.subgraph([n for n in graph.nodes if source in graph.nodes[n]["source_id"]]).copy()
    chunks.append({ "knowledge_graph_kwd": "subgraph", "source_id": [source], ... })
...
await thread_pool_exec(settings.docStoreConn.delete,
    {"knowledge_graph_kwd": ["graph", "subgraph"]}, index_name(tenant_id), kb_id)
...
await insert_chunks_bounded(chunks, tenant_id, kb_id, ...)    # LAST
```
```python
# utils.py:594-597 — batch pre-warm rationale
# Without this, set_graph spawns one asyncio task per entity, each calling
# embd_mdl.encode([single_name]).  For 17 k+ nodes that is 17 k round-trips.
# Pre-warming the cache here collapses N calls to ceil(N/_INSERT_BULK_SIZE).
```
```python
# utils.py:717-730 — edge deletion retries transient failures under the limiter
for attempt in range(max_retries):            # 3 attempts, backoff 2**attempt seconds
    try:
        async with chat_limiter:
            await thread_pool_exec(settings.docStoreConn.delete,
                {"knowledge_graph_kwd": ["relation"], "from_entity_kwd": from_node,
                 "to_entity_kwd": to_node}, ...)
        return
    except Exception as e:
        ...
        await asyncio.sleep(wait)
```

**Flow:** build graph snapshot chunk → regenerate every source doc's subgraph from the merged graph (so tier-A resume stays truthful after merges) → batch pre-warm embed cache for changed nodes ("A") and edges ("A->B: description" encode text) in `_INSERT_BULK_SIZE` batches under `chat_limiter` → per-item node/edge chunk tasks via gather with cancel-all-on-error and re-raise → delete old `{graph, subgraph}` rows → delete removed nodes in batches of 100 sorted names → delete removed edges with 3-attempt exponential-backoff retry → insert all new chunks bounded. Read side (`get_graph`) loads the single `"graph"` row; `removed_kwd=="Y"` triggers full `rebuild_graph`.
**Invariant:** Deletion happens only AFTER every new chunk exists in memory; a crash before the delete leaves the previous complete graph + valid subgraphs (resume replays); a crash between delete and insert leaves no graph rows but subgraph/checkpoint tiers still allow rebuild. Embedding work is rate-limited and cached so re-runs skip paid encodes; per-item task failure cancels siblings before raising (no half-written entity set).
**Probe:** No dedicated unit test for `set_graph` ordering at this pin (source-read-only caveat; inline invariant comments are decisive). Adjacent write-side pieces ARE tested: `test/unit_test/rag/graphrag/test_graphrag_utils.py::TestGraphNodeToChunk` pins entity-chunk fields; `TestNNeighbor` pins path enumeration feeding those chunks.

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", filePattern: "*graphrag/utils.py", query: "get_graph set_graph embedding vector store graph nodes edges pagerank n_hop", fields: ["lines"] });
// rank-1 = set_graph :550-755; rank-2 = get_graph :530-547; rank-3 = get_graph_doc_ids :518-527
```
Direct read: `rag/graphrag/utils.py` :495-824.

## Verdict
Adopt build-before-delete-before-insert ordering and the regenerated-subgraphs step (they keep per-doc resume honest after merges); adopt batch cache pre-warm before fan-out whenever per-item work hits an expensive model API. Adapt `_INSERT_BULK_SIZE`, retry counts/backoff, and limiter scope to host limits; omit the two-phase dance only if your store has real multi-row transactions across these kinds.
