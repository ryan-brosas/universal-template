<!-- capsule-v2 -->
# Incremental item skip — the content-hash status marker and its rollback twin

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does per-item incremental processing decide "already done" cheaply, and why must rollback EXCLUDE already-completed items?

## run_tasks_data_item_incremental
**Path/Symbol:** `cognee/modules/pipelines/operations/run_tasks_data_item.py:run_tasks_data_item_incremental` (:36-201), dispatcher `run_tasks_data_item` (:255-315).
**Signature:** yields `{run_info: PipelineRunAlreadyCompleted|PipelineRunCompleted|PipelineRunErrored, data_id}` dicts; chosen when `data_cache or incremental_loading`.
**Data Shape:** Skip marker is `data_point.pipeline_status[pipeline_name][str(dataset.id)] == DataItemStatus.DATA_ITEM_PROCESSING_COMPLETED` (JSON column on the relational Data row).

### Decisive source
```python
if data_point:
    if data_point.pipeline_status.get(pipeline_name, {}).get(str(dataset.id)) == \
            DataItemStatus.DATA_ITEM_PROCESSING_COMPLETED:
        yield {"run_info": PipelineRunAlreadyCompleted(...), "data_id": data_id}
        return
```
Pre-check resolves row + status in ONE session (NullPool-over-Neon economics documented inline): a carried `data_id` (DLT) looks up by id; otherwise bytes saved by this process reuse the hash computed at save time (`stored.metadata is None` → read file while open) and `identify_data_by_hash(content_hash, user, dataset.id)` scopes lookup to THIS dataset. Post-run, fresh content that had no row at pre-check is re-resolved inside the same session that writes the completed marker.

**Flow:** resolve data_id/content-hash → status pre-check (skip ⇒ AlreadyCompleted) → run tasks → write COMPLETED marker (merge+commit) → yield Completed; exceptions are logged, yielded as Errored, and re-raised unless `RAISE_INCREMENTAL_LOADING_ERRORS=false`.
**Invariant:** The rollback's `_extract_data_ids` deliberately EXCLUDES entries whose run_info is `PipelineRunAlreadyCompleted`: including them lets one bad file clear the markers of every record in the dataset (run_tasks hands rollback ALL results), so records extracted weeks earlier would be re-extracted at full LLM cost — while their nodes stay in the graph because node deletion is scoped by `pipeline_run_id`. The two halves of rollback must agree: marker says "not extracted", graph says otherwise ⇒ re-extraction storm.
**Probe:** `cognee/tests/unit/modules/cognify/test_rollback.py::test_extract_data_ids_skips_already_completed_items`; `cognee/tests/unit/modules/pipelines/test_run_tasks_data_item_sessions.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "run_tasks_data_item_incremental pipeline_status DATA_ITEM_PROCESSING_COMPLETED", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dataset-scoped hash-keyed completion markers + the AlreadyCompleted exclusion rule in rollback; adapt marker storage to your metadata store; omit the S3/Neon-specific single-session optimization rationale.
