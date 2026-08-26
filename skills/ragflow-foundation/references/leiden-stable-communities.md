<!-- capsule-v2 -->
# Leiden community determinism — how do you make graph partitioning reproducible across identical runs?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ragflow`. **Question:** What must be pinned (seed, node/edge ordering, component scope) so the same relationships always yield the same communities?

## Canonical ordering before partitioning
**Path/Symbol:** `rag/graphrag/general/leiden.py:_stabilize_graph` (:17-55), `stable_largest_connected_component` (:64-69), `_compute_leiden_communities` (:72-90), `run` (:93-137).
**Signature:** `def _compute_leiden_communities(graph, max_cluster_size: int, use_lcc: bool, seed=0xDEADBEEF) -> dict[int, dict[str, int]]`; `def run(graph: nx.Graph, args: dict) -> dict[int, dict[str, dict]]`.
**Data Shape:** Output: `{level: {community_id_str: {"weight": float, "nodes": [names]}}}`; per-community weight = Σ(node `"rank"` × node `"weight"`) normalized by the level max.

### Decisive source
```python
def _stabilize_graph(graph: nx.Graph) -> nx.Graph:
    fixed_graph = nx.DiGraph() if graph.is_directed() else nx.Graph()
    sorted_nodes = sorted(graph.nodes(data=True), key=lambda x: x[0])
    fixed_graph.add_nodes_from(sorted_nodes)
    edges = list(graph.edges(data=True))
    if not graph.is_directed():
        def _sort_source_target(edge):          # canonical (lesser, greater) endpoint order
            source, target, edge_data = edge
            if source > target:
                source, target = target, source
            return source, target, edge_data
        edges = [_sort_source_target(edge) for edge in edges]
    edges = sorted(edges, key=lambda x: f"{x[0]} -> {x[1]}")
    ...
```
```python
community_mapping = hierarchical_leiden(graph, max_cluster_size=max_cluster_size, random_seed=seed)
```

**Flow:** optionally restrict to the largest connected component (`use_lcc=True`, itself via `stable_largest_connected_component`) → rebuild the graph with sorted nodes and canonically-ordered undirected edges → `hierarchical_leiden` with fixed seed 0xDEADBEEF and `max_cluster_size` (12 at call site default) → group by partition level → weight-normalize each level.
**Invariant:** Identical relationship sets must produce identical partitions — hence BOTH a fixed random seed AND deterministic input ordering (networkx iteration order is insertion-order-dependent); nodes appearing in the map but missing from the live graph are skipped with a warning, never fatal.

## Get live surrounding code
**Retrieve:** (executed this pass)
```ts
await mcp.codebase_memory.search_graph({ project: "ragflow", query: "leiden communities stabilize largest connected component seed", fields: ["lines"] });
// rank-1..6 all leiden.py symbols: stable_largest_connected_component :64-69, _stabilize_graph :17-55, run :93-137
```
**Probe:** No direct unit test file for leiden.py at this pin — determinism is enforced by construction (sorted inputs + fixed seed). Coverage caveat recorded; treat as source-confirmed only.

## Verdict
Adopt sort-nodes + canonically-order-undirected-edges + fixed-seed partitioning as THE recipe for reproducible clustering; adapt `max_cluster_size`, level handling, and the rank×weight community scoring to your ranking model; omit graspologic specifics if your host ships another partitioner but keep the canonical-input invariant.
