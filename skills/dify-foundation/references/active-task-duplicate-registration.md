<!-- capsule-v2 -->
# active-task-duplicate-registration — How do you stop the same task from running twice in one process?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** What in-process guard prevents a duplicate concurrent workflow run under one task ID?

## RLock-guarded set with raise-on-duplicate context manager
**Path/Symbol:** `api/core/app/apps/workflow/active_workflow_tasks.py` (whole file, 38L); consumed at `api/core/app/apps/workflow/app_generator.py:687` (`with active_workflow_task(...)` around `runner.run()`).
**Signature:** `active_workflow_task(task_id: str) -> Generator[None]` (contextmanager); `get_active_workflow_task_count() -> int`; `reset_active_workflow_tasks()` for worker init/tests.
**Data Shape:** Module-level `_active_task_ids: set[str]` under a single `threading.RLock`; membership = "this process is executing this task".

### Decisive source
```python
@contextmanager
def active_workflow_task(task_id: str) -> Generator[None]:
    """Register a workflow application task ID for the duration of a workflow run."""
    if not task_id:
        raise ValueError("task_id must not be empty")
    with _active_task_ids_lock:
        if task_id in _active_task_ids:
            raise ValueError(f"Workflow task already active for task_id={task_id}")
        _active_task_ids.add(task_id)
    try:
        yield
    finally:
        with _active_task_ids_lock:
            _active_task_ids.discard(task_id)
```

**Flow:** worker thread starts → enters the context (raises on duplicate, registers otherwise) → runs the graph → exits via finally which always discards, even on exception. Count/clear helpers exist for graceful-shutdown checks and test isolation.
**Invariant:** Add-and-check are atomic under ONE lock acquisition — check-then-add without the lock is the race this exists to kill; discard-not-remove in finally means cleanup never raises; the guard is PROCESS-LOCAL by design (cross-process dedup is Redis/DB territory) and raising (not waiting) makes duplicate submission loud instead of latent.
**Probe:** `grep -c '_active_task_ids' core/app/apps/workflow/active_workflow_tasks.py` → 11; direct test `tests/unit_tests/core/app/apps/workflow/test_active_workflow_tasks.py::test_active_workflow_task_rejects_duplicate_task_id`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "active_workflow_task register task id already active", limit: 10 });
```

## Verdict
Adopt the atomic check-and-register context manager. Adapt storage scope (per-process set here) and whether duplicates should raise or queue. Omit nothing — it is 38 lines with zero dependencies.
