<!-- capsule-v2 -->
# Two-copy DAG state merge — How does a planner edit a running DAG without erasing execution progress?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** When an agent replaces its copy of the task graph while the orchestrator has already marked tasks COMPLETED, how do you merge so structure changes win but completions are never lost?

## Agent-structure base + orchestrator-execution overlay
**Path/Symbol:** `galaxy/session/observers/constellation_sync_observer.py:ConstellationModificationSynchronizer.merge_and_sync_constellation_states` (:384-451) with `_is_state_more_advanced` (:453-478).
**Signature:** `def merge_and_sync_constellation_states(self, orchestrator_constellation: TaskConstellation) -> TaskConstellation`.
**Data Shape:** two live copies of the same logical DAG — `self._current_constellation` (agent's, holds structural edits) vs the orchestrator's parameter (holds statuses/results/timestamps). Merge output becomes both sides' new truth.

### Decisive source
```python
# Use agent's constellation as base (has structural modifications)
merged = self._current_constellation

# Preserve execution state from orchestrator for existing tasks
for task_id, orchestrator_task in orchestrator_constellation.tasks.items():
    if task_id in merged.tasks:
        agent_task = merged.tasks[task_id]
        # Key: If orchestrator's task state is more advanced, preserve it
        if self._is_state_more_advanced(orchestrator_task.status, agent_task.status):
            agent_task._status = orchestrator_task.status
            agent_task._result = orchestrator_task.result
            agent_task._error = orchestrator_task.error
            agent_task._execution_start_time = orchestrator_task.execution_start_time
            agent_task._execution_end_time = orchestrator_task.execution_end_time
merged.update_state()
self._current_constellation = merged
```
with the advancement ladder:
```python
state_levels = {
    TaskStatus.PENDING: 0,
    TaskStatus.WAITING_DEPENDENCY: 1,
    TaskStatus.RUNNING: 2,
    TaskStatus.COMPLETED: 3,
    TaskStatus.FAILED: 3,   # Terminal states are equally advanced
    TaskStatus.CANCELLED: 3,
}
return level1 > level2
```

**Flow:** docstring names the race it prevents: orchestrator marks Task A COMPLETED → agent modifies the DAG while A still looks RUNNING in the agent's copy → naive replacement would resurrect A. The merge takes the agent's structure as base, then copies status/result/error/timestamps across for every shared task id whose orchestrator state is strictly more advanced; merged state is recomputed and re-published to both holders.
**Invariant:** execution state can only move forward along PENDING < WAITING_DEPENDENCY < RUNNING ≤ {COMPLETED, FAILED, CANCELLED}; terminal states are peers (level 3), so FAILED never overwrites COMPLETED and vice versa.
**Probe:** `tests/test_constellation_sync_observer.py:179-275` (`TestRaceConditionPrevention`) pins that the orchestrator's wait blocks until the agent publishes CONSTELLATION_MODIFIED, including out-of-order multi-task completion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", query: "merge and sync constellation states more advanced", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the advancement-ladder merge for any planner-editable plan representation. Adapt which per-task fields travel with execution state (UFO moves result, error, and both timestamps) and whether terminal states share one level. Omit the direct private-attribute writes (`_status`, `_result`) if your port has real setters — UFO reaches into privates because the classes lack a restore API.
