<!-- capsule-v2 -->
# extract_graph merge + orphan filter — entities group by (title, type) but edge validity checks title alone

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** after per-text-unit extraction, how are duplicate entities/relationships reconciled into one graph, and which hallucinated edges get dropped?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/extract_graph/extract_graph.py`: `extract_graph` (:23-73), `_merge_entities` (:104-115), `_merge_relationships` (:118-129); `utils.py`: `filter_orphan_relationships` (:142-182).
**Signature:** `_merge_entities(entity_dfs) -> pd.DataFrame` (columns title, type, description=list, text_unit_ids=list, frequency=count); `_merge_relationships(relationship_dfs)` (source, target, description=list, text_unit_ids=list, weight=SUM); `filter_orphan_relationships(relationships, entities) -> pd.DataFrame`.
**Data Shape:** entity identity = the PAIR (`title`, `type`) — same name typed PERSON and ORG stays two nodes; relationship identity = ordered pair (`source`, `target`) — A→B and B→A stay separate rows.

### Decisive source
```python
# entities: group by BOTH columns
.groupby(["title", "type"], sort=False)
.agg(description=("description", list),
     text_unit_ids=("source_id", list),
     frequency=("source_id", "count"))

# relationships: weight SUMS across text units (not max, not mean)
.groupby(["source", "target"], sort=False)
.agg(description=("description", list),
     text_unit_ids=("source_id", list),
     weight=("weight", "sum"))
...
entity_titles = set(entities["title"])             # ← TITLE only
mask = relationships["source"].isin(entity_titles) & relationships["target"].isin(entity_titles)
```

**Flow:** per-row `(entities_df, relationships_df)` results are concatenated → grouped/aggregated → relationships filtered against surviving entity titles → returned as the final graph tables. The orphan filter short-circuits empty inputs to a clean empty frame (`iloc[0:0]` reset), logs a warning count of dropped hallucinated edges, and resets index.
**Invariant:** (1) Entity merge key includes `type`; relationship-endpoint validity does NOT — an entity that exists under any type validates both endpoints. Porting this check to `(title,type)` pairs would silently drop real edges. (2) Relationship weight is additive across text units — downstream degree/rank math assumes it. (3) `sort=False` preserves first-seen order for deterministic output. (4) Descriptions become LISTS at merge time; the summarization op consumes exactly that shape.
**Probe:** `tests/unit/indexing/operations/test_extract_graph.py`: `test_groups_by_title_and_type` / `test_different_types_stay_separate` (:58-76), `test_groups_by_source_target` sum :89-96, orphan family :126-302 incl. cross-text-unit phantom `test_multi_text_unit_orphan` (:256-281) and index-reset pin (:283-302).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "_merge_entities _merge_relationships filter_orphan_relationships groupby frequency", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-level merge (pair-keyed entities, endpoint-summed edges, title-only orphan guard); adapt aggregation keys if the host ontology needs type-scoped edges; do not add a type-pair check to the filter without accepting the silent-edge-drop tradeoff.
