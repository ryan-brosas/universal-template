<!-- capsule-v2 -->
# Rollback handler — delete graph artifacts first, relational ownership second

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** In what order must a failed pipeline run be rolled back so a crash mid-rollback never leaves unrecoverable state?

## cognify_rollback_handler
**Path/Symbol:** `cognee/modules/cognify/rollback.py:cognify_rollback_handler` (:107-285), shared-slug filter (:194-232).
**Signature:** `async cognify_rollback_handler(pipeline_run_id: UUID, dataset, user=None, data_ingestion_info=None, **kwargs)`.
**Data Shape:** Node/Edge relational rows carry `(pipeline_run_id, dataset_id, slug, data_id)`; two engines: graph-provenance backends (refs live in the graph) vs ledger backends (Node/Edge rows + vector entries).

### Decisive source
```python
# Important ordering for robust retries:
# 1) Delete graph/vector artifacts first
# 2) Delete relational ownership rows and reset pipeline_status second
# If graph/vector deletion fails, relational rows remain as rollback metadata.
if unique_nodes or unique_edges:
    await delete_from_graph_and_vector(unique_nodes, unique_edges, is_legacy_node, is_legacy_edge)
async with db_engine.get_async_session() as session:
    ... delete Node/Edge where pipeline_run_id matches ... await _reset_pipeline_status(...)
```
Shared-slug guard: a target node/edge is deleted only if NO OTHER row (optionally dataset-scoped when multi-user) shares its slug — `select(distinct(slug)).where(slug.in_(targets), id.not_in(target_ids))`; only slugs unique to this run reach the graph/vector deletion.

**Flow:** resolve engine kind → (graph-provenance path) read affected data ids from source refs BEFORE the rollback removes them, `unified.rollback_by_pipeline_run_id`, reset statuses → (ledger path) load run's rows, partition out shared slugs, delete graph+vector for unique elements, then delete relational rows and clear `pipeline_status["cognify_pipeline"][dataset]` with `flag_modified`.
**Invariant:** Ordering is the contract — losing relational rows while graph artifacts survive is recoverable (rollback metadata gone ⇒ orphan sweep), but deleting ownership rows first makes a mid-crash leave unowned graph garbage that no sweeper can attribute. Startup recovery complements this: only runs whose LATEST status is DATASET_PROCESSING_STARTED are recovered (errored runs were already rolled back inline) and only past `STALE_RUN_MIN_AGE_SECONDS` (default 3600, env-overridable) so a live worker mid-deploy is never rolled back; missing created_at fails OPEN to recovery.
**Probe:** `cognee/tests/unit/modules/cognify/test_rollback.py::test_cognify_rollback_deletes_graph_before_relational`, `::test_cognify_rollback_keeps_relational_rows_if_graph_delete_fails`, `::test_rollback_preserves_markers_of_previously_extracted_data`; `cognee/tests/unit/modules/cognify/test_recovery.py::test_recover_stale_cognify_runs_skips_recent_run`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "cognify_rollback_handler _extract_data_ids rollback PipelineRunAlreadyCompleted", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt artifact-first/ownership-second ordering, shared-slug protection, STARTED-only stale-run recovery with an age threshold; adapt the ledger schema (Node/Edge rows vs in-graph refs) to your backend; omit Ladybug/unified-engine specifics.
