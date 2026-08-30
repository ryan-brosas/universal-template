<!-- capsule-v2 -->
# streaming finalize family — dedupe by natural key, stamp uuid + sequential human_readable_id, project to FINAL_COLUMNS

**Source:** graphrag MIT `main@60668ba946ccfd5cb784c578efedff86798a2c35`; Codebase Memory `graphrag`. **Question:** how do the finalize steps turn raw operation output into the stable parquet data model (ids, degrees, column order)?

## Connected graph-selected seam
**Path/Symbol:** `packages/graphrag/graphrag/index/operations/finalize_entities.py`: `finalize_entities` (:14-56); `finalize_relationships.py`: `finalize_relationships` (:70-111); `finalize_community_reports.py`: `finalize_community_reports` (:123-144); `data_model/schemas.py` (FINAL_COLUMNS lists :69-159).
**Signature:** `finalize_entities(entities_table: Table, degree_map: dict[str, int]) -> list[dict]`; `finalize_relationships(relationships_table, degree_map) -> list[dict]`.
**Data Shape:** entities keyed/deduped by `title`; relationships by `(source, target)`; `human_readable_id` = 0-based insertion counter; `id` = fresh `uuid4()` string per row; outputs projected to exactly ENTITIES/RELATIONSHIPS/COMMUNITY_REPORTS_FINAL_COLUMNS.

### Decisive source
```python
seen_titles: set[str] = set()
human_readable_id = 0
async for row in entities_table:
    title = row.get("title")
    if not title or title in seen_titles: continue
    seen_titles.add(title)
    row["degree"] = degree_map.get(title, 0)          # missing → 0, never KeyError
    row["human_readable_id"] = human_readable_id      # sequential, deterministic
    row["id"] = str(uuid4())                          # random, unique
    human_readable_id += 1
    out = {col: row.get(col) for col in ENTITIES_FINAL_COLUMNS}
    await entities_table.write(out)                   # same table: truncate=True temp-file swap
...
# relationships: combined_degree = degree(source) + degree(target), computed from NODE degrees
row["combined_degree"] = degree_map.get(key[0], 0) + degree_map.get(key[1], 0)
```
Reports: merge communities on `community` (adds parent/children/size/period), cast community→int, `human_readable_id = community`, `id = gen_sha512_hash(row, ["full_content"])`.

**Flow:** stream rows from the table → skip falsy/duplicate keys → enrich with degree(s) → assign both id forms → write projected row back through the SAME table handle (safe because writes go to a truncated temp then swap) → return ≤5 sample rows for logging.
**Invariant:** (1) Dedup happens BEFORE enrichment — first occurrence wins. (2) `human_readable_id` ordering is stream order, so it is reproducible only if upstream order is; uuids are not. (3) Edge `combined_degree` is DERIVED from node degrees at finalize time — recomputing it later from the pruned graph gives different numbers. (4) Report ids hash full_content — identical reports collapse to identical ids by design.
**Probe:** no dedicated unit files for the three finalizers (workflow-level coverage via `index/workflows/finalize_graph`); pinned by whole-file reads — coverage caveat recorded.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "finalize_entities finalize_relationships finalize_community_reports gen_sha512_hash human_readable_id", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt natural-key dedup + dual-id stamping + strict column projection as the storage-facing contract of any index pipeline; adapt key columns and id schemes to host; keep degree enrichment inside finalize where the FULL pre-prune degree map is still available.
