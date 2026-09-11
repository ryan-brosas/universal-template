<!-- capsule-v2 -->
# Community assembly workflow — cluster-to-table projection with intra-community edge ownership and numpy sanitization

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory project `graphrag`. **Question:** How do Leiden clusters become the `communities` table — entity membership, relationship/text-unit attribution, parent/children links, and serialization-safe rows?

## Key facts
**Path/Symbol:** `graphrag/index/workflows/create_communities.py` (`run_workflow` :25-52; `create_communities` :55-192; `_sanitize_row` :195-207). Inputs: `cluster_graph(relationships, max_cluster_size, use_lcc, seed)` (operations layer already mined in cluster-graph-determinism) → clusters as `(level, community, parent, title)` rows.
**Signature:** `create_communities(communities_table, entities_table, relationships, max_cluster_size, use_lcc, seed=None) -> list[dict]` (≤5 samples).
**Data Shape:** Output = `COMMUNITIES_FINAL_COLUMNS` incl. `id` (uuid4), `human_readable_id` == int community, `title` == f"Community {community}", `parent` (int), `children` (list), `entity_ids` (list), `relationship_ids` (sorted dedup list), `text_unit_ids` (sorted dedup list), `period` (ISO date), `size` (len entity_ids).

### Decisive source
```python
# create_communities.py :113-126 — relationships belong to a community ONLY when
# BOTH endpoints sit in it at that hierarchy level; processed one level at a time
# to keep intermediate DataFrames small (memory contract), concat once at the end.
for level in communities["level"].unique():
    level_comms = communities[communities["level"] == level]
    with_source = relationships.merge(level_comms, left_on="source", right_on="title", how="inner")
    with_both   = with_source.merge(level_comms, left_on="target", right_on="title", how="inner")
    intra = with_both[with_both["community_x"] == with_both["community_y"]]
    ...
    grouped = intra.explode("text_unit_ids").groupby(["community_x", "parent_x"]).agg(
        relationship_ids=("id", list), text_unit_ids=("text_unit_ids", list))
```
```python
# :165-179 — bidirectional tree: children aggregated per parent then merged back;
# NaN children replaced by [] so leaf communities serialize; period stamped for incremental tracking
final_communities["period"] = datetime.now(timezone.utc).date().isoformat()
final_communities["size"] = final_communities.loc[:, "entity_ids"].apply(len)
```
`_sanitize_row` (:195-207) converts np.ndarray→list, np.integer→int, np.floating→float BEFORE `table.write` — the table layer rejects numpy scalars.
**Flow:** cluster_graph → explode title lists → map titles→entity_ids via full entities-table scan → per-level intra-community edge grouping → sorted-set dedup of id lists → merge entity_ids → synthesize id/hrid/title/parent/children/period/size → sanitize each row → stream writes.
**Invariant:** edge ownership is per-LEVEL and requires both endpoints co-membership (an edge bridging two communities belongs to NONE); text_unit_ids dedup is REQUIRED because multiple intra edges share units; `children: []` for leaves is load-bearing (NaN breaks downstream readers); deterministic seed flows straight through to cluster_graph.
**Probe:** `tests/unit/indexing/test_create_communities.py` — 620L dedicated suite: (:145 all-final-columns, :193 title format, :206 hrid==community, :218 size==entity count, :255/:295 entity/relationship id attribution, :527 values-match-golden-file, :556 children populated, :572-603 ndarray/int/float sanitizer matrix).
**Retrieve:** `await mcp.codebase_memory.search_graph({ project: "graphrag", query: "create_communities intra community_x community_y _sanitize_row", limit: 10 })`

## Verdict
Adopt per-level both-endpoints-intra attribution, sorted-dedup id lists, bidirectional parent/children materialization, and pre-write numpy sanitization. Porters routinely get edge ownership wrong by attributing boundary edges — this capsule exists to stop that.
