<!-- capsule-v2 -->
# Dataset run engine — per-item concurrency, one lifecycle, fail-fast semantics

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does a dataset-scale run process items concurrently yet roll back as ONE logical run when any item fails?

## run_tasks (async generator over PipelineRunInfo)
**Path/Symbol:** `cognee/modules/pipelines/operations/run_tasks.py:run_tasks` (:37-254).
**Signature:** `async run_tasks(tasks | resolver, dataset_id, data=None, user=None, pipeline_name=..., incremental_loading=False, data_per_batch=20, rollback_handler=None, llm_config=None, embedding_config=None, data_cache=False)`.
**Data Shape:** Yields `PipelineRunStarted` → (per-item results folded into) `PipelineRunCompleted{data_ingestion_info}` or `PipelineRunErrored`; raises non-`PipelineRunFailedError` errors after yielding the errored event.

### Decisive source
```python
semaphore = asyncio.Semaphore(data_per_batch)

async def _run_item(data_item, item_tasks):
    async with semaphore:
        return await run_tasks_data_item(
            data_item, dataset, item_tasks, ...,
            PipelineContext(user=user, data_item=data_item, ...,
                # Copy per item: a shared dict would let one item's
                # ctx.extras mutations leak into every other item.
                extras=dict(extras) if isinstance(extras, dict) else {}),

# all scheduled at once; at most data_per_batch in flight:
gathered = await asyncio.gather(*[asyncio.create_task(_run_item(i, t)) for i, t in work_items])
```

**Flow:** log start → yield Started → open `operation_usage_scope()` + `parent_run_scope(run_id)` + `set_database_global_context_variables(dataset.id, owner)` context managers → resolve `(item, item_tasks)` pairs (validate each DISTINCT resolved list once via `id(item_tasks)` set — cognify's route resolver produces 3-4 shared lists) → gather under semaphore → separate successes from `BaseException` results → if ANY item errored raise `PipelineRunFailedError` (caught below: rollback + Errored yield, NOT re-raised) → flush durable storage (`push_to_s3` on engines that have it) BEFORE marking complete → yield Completed.
**Invariant:** (1) Flush-before-complete: an S3 push failure must be treated as run failure (rollback), never raised after the Completed event — two contradictory terminal events for one run is the bug this ordering prevents. (2) Per-item ctx.extras MUST be copied (`dict(extras)`); sharing leaks mutations across concurrent items. (3) Rollback handler runs inside try/except so a failing rollback cannot mask the original error. (4) The Started yield happens BEFORE global-context setup because background mode needs the started info immediately.
**Probe:** `cognee/tests/unit/modules/cognify/test_cognify_single_logical_run.py::test_run_tasks_resolver_shares_one_run_lifecycle`, `::test_run_tasks_validates_each_distinct_resolved_list_once`; `cognee/tests/unit/modules/pipelines/test_pipeline_context_extras.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "run_tasks semaphore data_per_batch gather work_items resolver", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt semaphore-bounded item concurrency with per-item copied extras, single-run lifecycle over mixed task lists, and flush-before-terminal-event ordering; adapt the relational logging calls and S3 push to your storage; omit telemetry specifics.
