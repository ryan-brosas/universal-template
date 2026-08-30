<!-- capsule-v2 -->

# Subflow reattach ladder — When does re-entering a subflow reuse the existing flow run instead of creating a new one?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** How do you prevent duplicate subflow runs on restarts while still allowing explicit reruns to execute fresh?

## Parent-task-run finality decides create-vs-attach

**Path/Symbol:** `src/prefect/flow_engine.py:FlowRunEngine.load_subflow_run (922-979)` (async twin `1620-1677`); called from `create_flow_run` after the synthetic tracking task run is created (:1006).

**Signature:** `load_subflow_run(parent_task_run: TaskRun, client: SyncPrefectClient, context: FlowRunContext) -> Union[FlowRun, None]`.

**Data Shape:** Query: `FlowRunFilter(parent_task_run_id={"any_": [parent_task_run.id]})`, `sort=FlowRunSort.EXPECTED_START_TIME_DESC`, `limit=1`. Rerun detection reads `context.flow_run.run_count > 1`.

### Decisive source
```python
# If the user explicitly triggered a re-run and the subflow did not
# complete, allow a fresh subflow to be created.
if (
    parent_task_run.state.is_final()
    and rerunning
    and not parent_task_run.state.is_completed()
):
    return None
...
if flow_runs:
    loaded_flow_run = flow_runs[0]
    # When the parent task run is final the subflow has already
    # finished; cache the result so the engine skips re-execution.
    if parent_task_run.state.is_final():
        self._return_value = loaded_flow_run.state
    return loaded_flow_run
```

**Flow:** subflow entry → synthesize a parent Task (`Task(name=..., fn=..., version=...)`) flagged `_is_subflow_tracking_task=True` → create its task run → ask load_subflow_run → (a) parent final AND rerunning AND parent NOT completed → return None ⇒ fresh flow run created · (b) existing run found AND parent final → attach + stash the old run's State into `self._return_value` so the engine short-circuits user-code execution and returns the cached result · (c) existing run found, parent non-final (e.g. process died mid-run) → attach WITHOUT caching, resuming against that run · (d) nothing found → None ⇒ create.

**Invariant:** (1) Attaching to a FINAL-parent subflow MUST also set `_return_value`; returning the run alone would still execute the function body again. (2) Only a FAILED (non-completed) parent on an explicit rerun unlocks freshness — a completed parent always replays its cached result even across reruns. (3) The tracking task carries `_is_subflow_tracking_task` so downstream layers can distinguish it from user tasks.

**Probe:** `grep -cF 'parent_task_run_id={"any_": [parent_task_run.id]}' src/prefect/flow_engine.py` → 2 (sync+async twins); `grep -cF '_is_subflow_tracking_task' src/prefect/flow_engine.py` → 2; `grep -c 'run_count > 1' src/prefect/flow_engine.py` → 2. Direct test: `tests/test_flow_engine.py:2050 TestLoadSubflowRun.test_sets_return_value_when_parent_task_run_is_final` (constructs real parent/child runs via client; asserts `result.id == child_run.id` AND `engine._return_value is not NotSet`).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "load_subflow_run reattach parent task run final", "limit": 4}'
```

## Verdict
Adopt the three-arm ladder (final+failed+rerun→fresh / found+final→attach+cache / found+running→resume) for any resumable nested-work unit keyed by a parent record; adapt the filter/sort fields to your store; omit the FlowRun-specific empirical-policy backfill around it.
