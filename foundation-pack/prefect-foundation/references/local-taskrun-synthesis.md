<!-- capsule-v2 -->

# Local task-run synthesis with uuid7 — How do sync tasks create their run record without touching the API, and why time-ordered IDs?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** What must a client-side TaskRun carry so dependency tracking works before the server ever sees it?

## In-memory TaskRun + Pending state, uuid7 id

**Path/Symbol:** `src/prefect/task_engine.py:_create_task_run_locally (133-226)`; id source `src/prefect/_internal/uuid7.py:uuid7`; dynamic key `src/prefect/_internal/engine.py:dynamic_key_for_task_run (13-33)`.

**Signature:** `_create_task_run_locally(task, id=None, parameters=None, flow_run_context=None, parent_task_run_context=None, wait_for=None, extra_task_inputs=None) -> TaskRun`.

**Data Shape:** `task_inputs: dict[str, set[RunInput]]` built from three sources — per-parameter `collect_task_run_inputs_sync(v)`, `"__parents__"` from `_infer_parent_task_runs(...)` (context-inferred upstream task runs), and `"wait_for"`. No flow-run context ⇒ `dynamic_key = f"{task.task_key}-{uuid4().hex}"`, name = plain task name; with context ⇒ counter-based dynamic key and name suffixed `-<dynamic_key[:3]>`.

### Decisive source
```python
dynamic_key = dynamic_key_for_task_run(
    context=flow_run_context, task=task, stable=False
)
...
task_run_id = id or uuid7()
state = prefect.states.Pending(
    state_details=StateDetails(
        task_run_id=task_run_id,
        flow_run_id=flow_run_id,
    )
)
```

**Flow:** resolve contexts (defaulting to `.get()`) → compute dynamic key (detached/remote ⇒ random uuid4 string; autonomous ⇒ task's own dynamic_key stored into `context.task_run_dynamic_keys`; in-flow ⇒ monotonically increasing int per task_key) → collect inputs from parameters + inferred parents + wait_for → merge `extra_task_inputs` via set-union → build Pending State whose `state_details` back-reference BOTH run ids → assemble TaskRun with empirical policy from the task (retries/delay/jitter), tags = task.tags ∪ TagsContext tags, timestamps stamped from the state.

**Invariant:** (1) The id is **uuid7** (time-ordered) — sorting task runs by id approximates creation order even before the server assigns anything; a random v4 would scramble retry/retry-diagnostic ordering. (2) `state_details.task_run_id`/`flow_run_id` must be populated at CREATION because events emitted later derive identity from them. (3) The async engine uses `await self.task.create_local_run(...)` instead of this helper but produces the same shape; both paths emit the Pending event INSIDE `setup_run_context` so `copy_context()` captures THIS task's TaskRunContext rather than an enclosing parent's (:847-857 comment).

**Probe:** `grep -cF '_create_task_run_locally' src/prefect/task_engine.py` → 2; `grep -cF 'uuid7()' src/prefect/task_engine.py` → 1. Direct tests: `tests/test_task_engine.py:432 test_task_tracks_nested_parent_as_dependency` and `tests/test_tasks.py:3652 TestSubflowWaitForTasks.test_backend_task_inputs_includes_wait_for_tasks` (wait_for lands in backend-visible task_inputs).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "task run local uuid7 dynamic_key", "limit": 4}'
```

## Verdict
Adopt client-side run-record synthesis with time-ordered ids for any offline-capable execution ledger; adapt the input-collection taxonomy to your dependency model; omit Prefect's RunInput schema specifics.
