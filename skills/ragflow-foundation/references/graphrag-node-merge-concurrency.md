<!-- capsule-v2 -->
# GraphRAG node merge under concurrency — how do you fold duplicate entity nodes into one without tripping networkx live-adjacency mutation?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** What must a porter snapshot/serialize when merging resolved entity nodes in a shared `nx.Graph`?

## Snapshot neighbours, serialize merges, track redirected edges
**Path/Symbol:** `rag/graphrag/general/extractor.py:Extractor._merge_graph_nodes` (:292-336); serialization at `rag/graphrag/entity_resolution.py:limited_merge_nodes` (:170-179).
**Signature:** `async def _merge_graph_nodes(self, graph: nx.Graph, nodes: list[str], change: GraphChange, task_id="")` — `nodes[0]` survives, `nodes[1:]` are folded into it.
**Data Shape:** Node attrs: `description` (joined with `<SEP>`), `source_id` (sorted unique list), `entity_type`, later `pagerank`. Edge attrs: `weight` (summed), `description`, `keywords`, `source_id`. `GraphChange` records added_updated/removed nodes+edges for downstream store updates.

### Decisive source
```python
node0_neighbors = set(graph.neighbors(nodes[0]))
for node1 in nodes[1:]:
    # Snapshot neighbors before mutation; otherwise networkx raises
    # "dictionary keys changed during iteration" when concurrent merges
    # or graph.add_edge/remove_node below touch the same adjacency dict.
    for neighbor in list(graph.neighbors(node1)):
        change.removed_edges.add(get_from_to(node1, neighbor))
        if neighbor not in nodes_set:
            edge1_attrs = graph.get_edge_data(node1, neighbor)
            if neighbor in node0_neighbors:
                edge0_attrs = graph.get_edge_data(nodes[0], neighbor)
                edge0_attrs["weight"] += edge1_attrs["weight"]
                ...
            else:
                graph.add_edge(nodes[0], neighbor, **edge1_attrs)
                # Track the redirected neighbour so a later node1 ... takes
                # the merge branch above instead of overwriting the edge.
                node0_neighbors.add(neighbor)
    graph.remove_node(node1)
```
```python
async def limited_merge_nodes(graph, nodes, change):
    async with merge_lock:            # asyncio.Lock — merges are serialized
        await self._merge_graph_nodes(graph, nodes, change, task_id)
```

**Flow:** resolution produces "same-as" pairs → `nx.connected_components(connect_graph)` groups them → each component merges serially under the lock → surviving node accumulates descriptions/source_ids, edges are re-pointed or weight-merged → pagerank recomputed once after all merges (`nx.pagerank` stored as per-node `"pagerank"` attr — the value the retrieval-side tag/pagerank capsule consumes).
**Invariant:** Never iterate a live adjacency view while mutating the graph — snapshot with `list(...)`; after redirecting an edge to the survivor, add the neighbor to the survivor's neighbor set so duplicate edges MERGE (sum weights) rather than overwrite; every removal is recorded in `GraphChange`.

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "extractor gleaning continuation loop max tokens record", filePattern: "rag/graphrag/general/*", fields: ["lines","signature"] });  // locates _merge_graph_nodes :292-336
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "is_similarity candidate pairs resolution Levenshtein", fields: ["lines"] });  // rank-2 _resolve_candidate; merge site context
```
**Probe:** `test/unit_test/rag/graphrag/test_merge_graph_nodes.py` — regression tests pin exactly this: dense-neighbourhood merge keeps all 20 neighbours on the survivor; shared-neighbour mutation-during-iteration case; two concurrent merges under `Semaphore(1)` both succeed.

## Verdict
Adopt snapshot-before-mutate + survivor-neighbor-set tracking + lock-serialized merges and GraphChange bookkeeping; adapt the LLM re-summarization of merged descriptions (here `_handle_entity_relation_summary` only fires past 12 joined descriptions, 512-token truncation) to your budget; omit nothing behavioral — the test file pins this seam directly.
