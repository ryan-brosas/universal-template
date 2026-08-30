<!-- capsule-v2 -->
# union-find LCC — path-compressed components sized over the deduplicated edge list

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** what is the cheapest correct way to get the largest connected component (and all components) of a DataFrame edge list without pulling in a graph library?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/graphs/connected_components.py`: `connected_components` (:63-116), `largest_connected_component` (:119-147).
**Signature:** `connected_components(relationships: pd.DataFrame, source_column="source", target_column="target") -> list[set[str]]`; `largest_connected_component(...) -> set[str]`.
**Data Shape:** returns components as node-title sets sorted by DESCENDING size; LCC = element [0]; empty input → empty list / empty set.

### Decisive source
```python
edges = relationships.drop_duplicates(subset=[source, target])   # dedupe FIRST
all_nodes = pd.concat([edges[source], edges[target]]).unique()
parent = {node: node for node in all_nodes}
def find(x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]      # path compression (halving)
        x = parent[x]
    return x
def union(a, b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[ra] = rb           # no rank/size heuristic — fine at this scale
...
return sorted(groups.values(), key=len, reverse=True)   # biggest first
```

**Flow:** drop duplicate edges → collect the distinct node universe from BOTH columns → union each edge → group nodes by final root → sort groups by size descending. Callers treat `[0]` as "the" largest component (ties broken by sort stability).
**Invariant:** component membership is computed on the DEDUPLICATED edge list — duplicates never inflate anything; isolated entities (degree 0) never appear here because they have no edges (the prune op re-inserts them with degree 0 explicitly). Union order affects internal parent pointers but never the resulting partition.
**Probe:** pinned indirectly via `tests/unit/indexing/test_cluster_graph.py::test_lcc_filters_to_largest_component` (:69-83) and `tests/unit/indexing/test_cluster_graph.py::TestClusterGraphRealData` real-data runs; no dedicated direct unit file for connected_components.py (caveat recorded).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "connected_components largest_connected_component find union path compression", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dependency-free union-find LCC for pandas edge lists (path compression is enough at knowledge-graph scale); adapt to weighted/ranked variants only if needed; omit rank-based union — the repo proves partition correctness doesn't need it.
