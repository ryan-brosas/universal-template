<!-- capsule-v2 -->
# Background pipeline anchoring — strong refs or the GC eats your run

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** Why can a fire-and-forget `asyncio.create_task` silently vanish, and what is the minimal fix?

## run_pipeline_as_background_process
**Path/Symbol:** `cognee/modules/pipelines/layers/pipeline_execution_mode.py:run_pipeline_as_background_process` (:54-127), `_BACKGROUND_PIPELINE_TASKS` (:21), selector `get_pipeline_executor` (:130-140).
**Signature:** `get_pipeline_executor(run_in_background: bool)` returns blocking or background runner; background runner returns `{dataset_id: PipelineRunStarted}` immediately.
**Data Shape:** Module-level `set[asyncio.Task]`; tasks self-remove on done so set size tracks running pipelines.

### Decisive source
```python
# Strong refs for fire-and-forget background pipeline tasks. The event loop only
# keeps weak references to tasks, so without anchoring here Python's gc can collect
# an in-flight task before it completes, silently aborting the background run.
_BACKGROUND_PIPELINE_TASKS: set[asyncio.Task] = set()
...
task = asyncio.create_task(handle_rest_of_the_run(pipeline_list=pipeline_list))
_BACKGROUND_PIPELINE_TASKS.add(task)
task.add_done_callback(_BACKGROUND_PIPELINE_TASKS.discard)
```

**Flow:** For each dataset a pipeline generator is created; `await anext(pipeline_run)` pulls exactly ONE item (the Started event) synchronously so the caller gets immediate handles; payloads are stripped (`payload = []`) to avoid serializing raw data; remaining events are drained by the anchored task and pushed to `pipeline_run_info_queues` keyed by run id.
**Invariant:** (1) The anchor is not optional decoration — dropping it is an intermittent silent-death bug that no exception handler ever sees. (2) Pipelines are advanced SEQUENTIALLY in one task (`for pipeline in pipeline_list`) to avoid database write conflicts — parallelizing this needs the queue mechanism first. (3) The blocking twin aggregates `{dataset_id: last run_info}` via `getattr(run_info, "dataset_id", None)`.
**Probe:** `cognee/tests/unit/modules/pipelines/test_background_pipeline_task_anchoring.py` (whole file pins anchoring + self-discard).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "run_pipeline_as_background_process _BACKGROUND_PIPELINE_TASKS", limit: 3, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the anchor-set + done-callback pattern verbatim for any create_task-and-forget; adapt queue push to your progress-reporting channel; omit cognee's payload-stripping TODO.
