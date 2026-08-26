<!-- capsule-v2 -->
# prune_graph ordered thresholds — degree cuts first, frequency stats computed on survivors, edge-weight percentile last

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** in which order do graph-pruning filters apply, and why does the order change the result?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/prune_graph.py`: `prune_graph` (:131-223), `_get_upper_threshold_by_std` (:226-232).
**Signature:** `prune_graph(entities, relationships, min_node_freq=1, max_node_freq_std=None, min_node_degree=1, max_node_degree_std=None, min_edge_weight_pct=40, remove_ego_nodes=False, lcc_only=False) -> tuple[pd.DataFrame, pd.DataFrame]`.
**Data Shape:** operates on merged entity/relationship frames (`title`, NODE_FREQUENCY column, `source`, `target`, EDGE_WEIGHT); returns reset-index copies.

### Decisive source
```python
degree_df = compute_degree(relationships)
degree_map = dict(zip(degree_df["title"], degree_df["degree"], strict=True))
entity_titles = set(entities["title"])
for t in entity_titles:
    degree_map.setdefault(t, 0)          # isolated entities join the population
...
if remove_ego_nodes and degree_map:
    nodes_to_remove.add(max(degree_map, key=lambda n: degree_map[n]))   # ONE ego node
# degree-based removals FIRST:
remaining = entities[~entities["title"].isin(nodes_to_remove)]
# THEN frequency thresholds over the SURVIVORS ("NX mutates sequentially" comment):
low_freq = remaining.loc[remaining[freq_col] < min_node_freq, "title"]
...
upper = _get_upper_threshold_by_std(freq_values, max_node_freq_std)     # mean + k·std
# edge weights: percentile floor
min_weight = np.percentile(pruned_rels[EDGE_WEIGHT].to_numpy(), min_edge_weight_pct)
pruned_rels = pruned_rels[pruned_rels[EDGE_WEIGHT] >= min_weight]
```

**Flow:** degrees computed from the raw edge list (isolated entities seeded at 0 so statistics see the full population) → optional single-ego removal → below-min-degree removal → std-based upper-degree trim → survivors become the population for frequency floors/std-trims → final entity set drives edge endpoint filtering → edge-weight percentile floor → optional LCC restriction.
**Invariant:** (1) Filters are SEQUENTIAL — each threshold's mean/std is computed over nodes that survived prior filters; reordering changes both the statistics and the outcome. (2) Degree comes from edges only; zero-degree entities exist in the map but never rank as ego. (3) Percentile floor uses `>=` — exactly-at-threshold edges survive.
**Probe:** no direct unit file for prune_graph (config pins at `tests/unit/config/utils.py::assert_extract_graph_nlp_configs` :210-215); pinned by whole-file read — coverage caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "prune_graph _get_upper_threshold_by_std min_edge_weight_pct remove_ego_nodes lcc_only", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt sequential-filter pruning with survivor-scoped statistics (and explicit isolated-node seeding); adapt threshold defaults to host corpora; document in any port that filter ORDER is part of the contract, not an implementation detail.
