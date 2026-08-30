<!-- capsule-v2 -->
# Task execution error funnel — How should a task runner report failures so the DAG still advances?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** When an individual task throws (timeout, config error, anything), how do you keep dependents bookkeeping correct and observers informed instead of losing the task to an unhandled exception?

## Two-layer funnel: result conversion, then completion-always
**Path/Symbol:** `galaxy/constellation/task_star.py:TaskStar.execute` (:190-256) and `galaxy/constellation/orchestrator/orchestrator.py:TaskConstellationOrchestrator._execute_task_with_events` (:603-696).
**Signature:** `async def execute(self, device_manager: ConstellationDeviceManager) -> ExecutionResult`; `async def _execute_task_with_events(self, task: TaskStar, constellation: TaskConstellation) -> None`.
**Data Shape:** `ExecutionResult(task_id, status: TaskStatus, error: Exception|None, start_time, end_time, metadata)`; `is_success = result.status == TaskStatus.COMPLETED.value` (note: `.value`, a string comparison).

### Decisive source
Layer 1 — TaskStar.execute converts instead of raising:
```python
except asyncio.TimeoutError as e:
    return ExecutionResult(
        task_id=self.task_id, status=TaskStatus.FAILED,
        error=TimeoutError(f"Task execution timeout: {e}"),
        start_time=start_time, end_time=end_time,
        metadata={"device_id": self.target_device_id})
except AttributeError as e:
    return ExecutionResult(... error=AttributeError(f"Configuration error: {e}") ...)
except Exception as e:
    return ExecutionResult(... status=TaskStatus.FAILED, error=e ...)
```

Layer 2 — the orchestrator marks the graph complete on BOTH paths:
```python
try:
    await self._event_bus.publish_event(TaskEvent(event_type=EventType.TASK_STARTED, ...))
    task.start_execution()
    result = await task.execute(self._device_manager)
    is_success = result.status == TaskStatus.COMPLETED.value
    newly_ready = constellation.mark_task_completed(
        task.task_id, success=is_success, result=result)
    await self._event_bus.publish_event(
        TaskEvent(event_type=(EventType.TASK_COMPLETED if is_success
                              else EventType.TASK_FAILED), ...))
except Exception as e:
    newly_ready = constellation.mark_task_completed(
        task.task_id, success=False, error=e)
    await self._event_bus.publish_event(
        TaskEvent(event_type=EventType.TASK_FAILED, ..., error=e))
    raise
```

**Flow:** publish TASK_STARTED → start_execution() → execute → classify success from the result's *status value* → mark_task_completed (which promotes dependents) → publish TASK_COMPLETED or TASK_FAILED carrying `newly_ready_tasks`; if anything above escaped as an exception, still mark failure + publish TASK_FAILED before re-raising so the future's exception is visible to cancellation/reaping.
**Invariant:** every started task ends with exactly one terminal bookkeeping call (`mark_task_completed`) and exactly one terminal event; dependent promotion must happen even for failures because edges evaluate conditions against errors too.
**Probe:** direct-test coverage caveat: no dedicated upstream suite pins `_execute_task_with_events` end-to-end at this pin (`tests/test_orchestrator_refactored.py` covers orchestration with mocked execution); behavior is pinned by reading both ranges plus `mark_task_completed` (:436-481). Coverage check returned `no_recorded_issue` for all cited files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", query: "execute task events mark completed failed", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the two-layer funnel: leaf executors return failure results rather than raising for expected failure classes; the scheduler treats "terminal bookkeeping + terminal event" as unconditional. Adapt the exception→result mapping taxonomy to your domain and fix UFO's latent string-vs-enum comparison (`TaskStatus.COMPLETED.value`) in a typed port. Omit the device-manager metadata payload.
