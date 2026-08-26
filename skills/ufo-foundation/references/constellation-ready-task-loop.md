<!-- capsule-v2 -->
# Constellation ready-task claim loop — How do you schedule DAG-ready tasks concurrently without double-executing or starving?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** How does an async orchestrator run many independent tasks at once while guaranteeing each is scheduled exactly once and new ready tasks appear as dependencies complete?

## Ready-task claim loop over a dedup map
**Path/Symbol:** `galaxy/constellation/orchestrator/orchestrator.py:TaskConstellationOrchestrator._run_execution_loop` (:394-432), `_schedule_ready_tasks` (:468-482), `_wait_for_task_completion` (:484-497).
**Signature:** `async def _run_execution_loop(self, constellation: TaskConstellation) -> None`; `_schedule_ready_tasks(self, ready_tasks: List[TaskStar], constellation: TaskConstellation) -> None`.
**Data Shape:** `_execution_tasks: Dict[str, asyncio.Task]` keyed by task id — the claim registry; readiness comes from `constellation.get_ready_tasks()` (dependency-satisfied + priority-sorted).

### Decisive source
```python
while not constellation.is_complete():
    if self._cancellation_requested or self._cancelled_constellations.get(...):
        constellation.state = ConstellationState.CANCELLED
        break
    constellation = await self._sync_constellation_modifications(constellation)
    self._validate_existing_device_assignments(constellation)
    ready_tasks = constellation.get_ready_tasks()
    await self._schedule_ready_tasks(ready_tasks, constellation)
    await self._wait_for_task_completion()
await self._wait_for_all_tasks()
```
and the claim guard:
```python
for task in ready_tasks:
    if task.task_id not in self._execution_tasks:
        task_future = asyncio.create_task(
            self._execute_task_with_events(task, constellation))
        self._execution_tasks[task.task_id] = task_future
```

**Flow:** loop iteration = cancellation check → merge pending agent edits → re-validate device assignments → snapshot ready tasks → create futures for not-yet-claimed ids → block until ANY future completes → clean up done futures; when no futures exist the wait sleeps 0.1 s so the loop can't spin; after exit, `_wait_for_all_tasks` drains stragglers.
**Invariant:** a task id enters `_execution_tasks` at most once per execution run; the loop must re-read readiness every iteration because completions and external edits change it between iterations.
**Probe:** `tests/galaxy/constellation/test_orchestrator_cancellation.py:121-203` pins that the loop checks both the global flag and the per-constellation flag each iteration and stops immediately on cancellation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", query: "run execution loop schedule ready tasks", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the shape: readiness recomputed per iteration + claim-by-id dedup map + FIRST_COMPLETED batching. Adapt the 0.1 s idle sleep to your event-loop idioms and add your own concurrency cap (UFO relies on the DAG itself for bounding). Omit the UFO-specific modification-sync and device-validation hooks unless you also port those planes.
