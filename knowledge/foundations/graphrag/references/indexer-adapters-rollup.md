<!-- capsule-v2 -->
# Indexer→query adapters — how do parquet tables become query objects, and where does the community-level rollup actually happen?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** what transformations do read_indexer_* perform (level filtering, community roll-up, embedding fail-open) that a porter must preserve or search quality silently degrades?

## adapter set over dfs loaders
**Path/Symbol:** `packages/graphrag/graphrag/query/indexer_adapters.py` (`read_indexer_entities` :120-159, `read_indexer_reports` :74-103, `read_indexer_communities` :162-197, `read_indexer_relationships` :63-71, `read_indexer_covariates` :45-60, `read_indexer_text_units` :36-42, `read_indexer_report_embeddings` :106-117, `embed_community_reports` :200-216, `_filter_under_community_level` :219-225).
**Signature:** each `read_indexer_*(final_*: pd.DataFrame, ...) -> list[DataModel]`; thin wrappers over `query/input/loaders/dfs.py`.
**Data Shape:** entities gain a LIST-valued `community` column (set of str ids); reports are filtered to max-level communities; relationships rank from `combined_degree`.

### Decisive source
```python
# indexer_adapters.py:91-101 — NON-dynamic selection ROLLS UP to the
# deepest community an entity belongs to: fillna(-1) first (NaN = no
# community), groupby title → max(community), then INNER-join keeps only
# reports whose id survives; without this, level-capped queries return
# empty report sets
nodes_df.loc[:, "community"] = nodes_df["community"].fillna(-1)
nodes_df.loc[:, "community"] = nodes_df["community"].astype(int)
nodes_df = nodes_df.groupby(["title"]).agg({"community": "max"}).reset_index()
reports_df = reports_df.merge(filtered_community_df, on="community", how="inner")
```
```python
# :111-117 — DRIFT's full-content embeddings attach PER REPORT with a
# catch-all except → None: missing embeddings degrade to unembedded
# reports instead of failing the whole query load
try:
    report.full_content_embedding = embeddings_store.search_by_id(report.id).vector
except (IndexError, Exception):  # noqa: BLE001
    report.full_content_embedding = None
```

**Flow:** CLI/API loads parquet DataFrames → adapters explode `entity_ids`, join communities↔entities↔reports, apply `_filter_under_community_level` (`df[df.level <= community_level]`) → per-model dedup (`drop_duplicates(subset=["id"])`) → typed model lists handed to engine factories. Missing-report communities are DROPPED with a warning in read_indexer_communities (:174-183) — the hierarchy never references report-less nodes.
**Invariant:** entity community values become STRINGS via `[str(int(i)) for i in x]` (:140-142) after set-aggregation — porters keeping ints break context-builder formatting that interpolates community ids into text; covariates arrive as `{"claims": [...]}` dict keyed by the consumer (api/query passes it straight through).
**Probe:** no dedicated unit file (adapters covered at workflow level by tests/unit/query + update-chain suites). Pinned @pin by source greps: `grep -c 'agg({"community": "max"})' indexer_adapters.py` = 1, `grep -c 'agg({"community": set})'` = 1, `grep -c 'except (IndexError, Exception)'` = 1. Recorded caveat: verified by direct read; behavior indirectly exercised by query-context unit tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "read indexer reports embeddings full content", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved rank#1 `read_indexer_report_embeddings` :106-117.

## Verdict
Adopt the roll-up-to-max-community rule, string-normalized entity community lists, and fail-open embedding attachment as ONE unit (they jointly define what "load index outputs" means); adapt column names to your storage; omit covariate plumbing if claims are unused.
