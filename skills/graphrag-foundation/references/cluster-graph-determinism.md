<!-- capsule-v2 -->
# cluster_graph determinism — normalize→dedup(keep=last)→LCC→sorted edge list BEFORE the fixed-seed Leiden call

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how does community detection stay reproducible when the same graph arrives with different row order, reversed edges, or duplicate rows?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/cluster_graph.py`: `cluster_graph` (:20-47), `_compute_leiden_communities` (:51-99); `graphs/stable_lcc.py`: `stable_lcc` (:22-70), `_normalize_name` (:73-75); `graphs/hierarchical_leiden.py`: `hierarchical_leiden` (:11-26).
**Signature:** `cluster_graph(edges: pd.DataFrame, max_cluster_size: int, use_lcc: bool, seed: int | None = None) -> Communities` where `Communities = list[tuple[level: int, cluster: int, parent: int, nodes: list[str]]]`.
**Data Shape:** output tuples are (level, cluster_id, parent_cluster_id, member node titles); root clusters carry `parent = -1`.

### Decisive source
```python
# undirected normalization BEFORE clustering — replicate NX keep-last semantics
lo = edge_df[["source", "target"]].min(axis=1)
hi = edge_df[["source", "target"]].max(axis=1)
edge_df["source"], edge_df["target"] = lo, hi
edge_df.drop_duplicates(subset=["source", "target"], keep="last", inplace=True)
if use_lcc:
    edge_df = stable_lcc(edge_df)          # unescape→upper→strip names too
edge_list = sorted(zip(edge_df["source"].astype(str),
                       edge_df["target"].astype(str), weights, strict=True))
community_mapping = hierarchical_leiden(edge_list, max_cluster_size=max_cluster_size,
                                        random_seed=seed)
```
`hierarchical_leiden` fixes the native call: `seed=0xDEADBEEF default, resolution=1.0, randomness=0.001, use_modularity=True, iterations=1`.
`stable_lcc` order: copy → normalize node names (`html.unescape().upper().strip()`) → filter to largest component → swap so lesser node is source → dedupe → sort by (source, target).

**Flow:** edges normalized/deduped → optional LCC restriction → fully sorted `(src, tgt, weight)` triples feed graspologic's Leiden → per-partition results folded into `{level: {node: cluster}}` maps plus `{cluster: parent}` hierarchy (None parent → -1 sentinel).
**Invariant:** identical input SETS produce identical communities regardless of row order/reversal/duplicates — because everything downstream of normalization is sorted and the RNG seed is pinned. Dropping the sort or passing raw edge order makes runs non-reproducible even WITH a fixed seed.
**Probe:** `tests/unit/indexing/test_cluster_graph.py`: `test_same_seed_same_result` (:154), `test_does_not_mutate_input` (:169), `test_reversed_edges_produce_same_result` (:94), `test_duplicate_edges_are_deduped` (:121), `test_missing_weight_defaults_to_one` (:134), `test_lcc_filters_to_largest_component` (:69), `test_level_zero_has_parent_minus_one` (:204), `test_all_nodes_covered_at_each_level` (:220).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "cluster_graph _compute_leiden_communities hierarchical_leiden stable_lcc Communities", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt canonicalize-before-cluster (direction normalize + keep-last dedup + name normalization + total sort + pinned seed) for ANY stochastic graph algorithm; adapt thresholds/resolution to host; note the LCC step intentionally discards smaller components when `use_lcc` is set.
