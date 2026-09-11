<!-- capsule-v2 -->
# Qualification gate — dataset status short-circuits and their bypass rule

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does a pipeline avoid double-processing a dataset, and when MUST that check be skipped?

## check_pipeline_run_qualification
**Path/Symbol:** `cognee/modules/pipelines/layers/check_pipeline_run_qualification.py:check_pipeline_run_qualification` (:19-56); consumer `pipeline.py:_run_body` (:129-159); recovery interplay `reset_pipeline_run_status`.
**Signature:** `async (dataset: Dataset, data: list[Data], pipeline_name: str) -> Optional[PipelineRunStarted | PipelineRunCompleted]` (None ⇒ proceed).
**Data Shape:** `PipelineRunStatus.DATASET_PROCESSING_STARTED` ⇒ in-flight elsewhere; `DATASET_PROCESSING_COMPLETED` ⇒ already done. Returns the EXISTING run's info with its payload intact for Started.

### Decisive source
```python
if use_pipeline_cache:
    # Caching path: if this dataset's pipeline is already running or has already
    # completed, return that status instead of re-processing.
    # When caching is disabled the run always proceeds — concurrent runs are kept
    # safe by the per-dataset lock, NOT by this check:
    process_pipeline_status = await check_pipeline_run_qualification(dataset, body_data, pipeline_name)
    if process_pipeline_status:
        yield process_pipeline_status
        return
```

**Flow:** gated behind `use_pipeline_cache=True` (cognify passes `use_pipeline_cache=False` at cognify.py :330 — every cognify call is a fresh logical run; per-dataset lock provides safety) → status lookup → map STARTED/COMPLETED to early-return events. Startup recovery resets lingering STARTED statuses (`recover_stale_cognify_runs_on_startup`) so a crashed run doesn't block re-runs forever via this gate.
**Invariant:** (1) The qualification check is an OPTIMIZATION, never the concurrency-safety mechanism — the dataset lock owns mutual exclusion; confusing these two roles deadlocks or duplicates work. (2) A stale STARTED row must be clearable (recovery path) or the gate becomes a permanent denial of service after any crash. (3) Early-returned events must carry the ORIGINAL pipeline_run_id so callers correlate against the live/previous run rather than minting one.
**Probe:** `cognee/tests/test_pipeline_cache.py`; `cognee/tests/unit/modules/cognify/test_cognify_single_logical_run.py::test_task_resolver_composes_with_pipeline_cache`.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "check_pipeline_run_qualification DATASET_PROCESSING_COMPLETED use_pipeline_cache", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt status-gated short-circuit as opt-in optimization with lock-owned exclusion; adapt status vocabulary; omit if your runner serializes runs externally anyway.
