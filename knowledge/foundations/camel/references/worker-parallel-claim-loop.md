<!-- capsule-v2 -->
# Worker parallel claim loop — How does a worker node run many tasks concurrently yet never claim the same task twice?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** Where is the concurrency boundary in a worker, and what guarantees per-task cleanup on failure?

## Poll-with-timeout + fire-and-forget processing tasks
**Path/Symbol:** `camel/societies/workforce/worker.py:Worker._listen_to_channel` (:151-205), `_process_single_task` (:109-148).
**Signature:** `async def _listen_to_channel(self)` decorated `@check_if_running(False)`; abstract `_process_task(task, dependencies, stream_callback) -> TaskState`.
**Data Shape:** `_active_task_ids: Set[str]`, `_running_tasks: Set[asyncio.Task]`; channel claim via `get_assigned_task_by_assignee(node_id)` (atomic SENT→PROCESSING).

### Decisive source
```python
task = await asyncio.wait_for(self._get_assigned_task(), timeout=1.0)
task_coroutine = asyncio.create_task(self._process_single_task(task))
self._running_tasks.add(task_coroutine)
...
# _process_single_task:
try:
    task_state = await self._process_task(task, task.dependencies, stream_callback=_on_chunk)
    task.set_state(task_state)
    await self._channel.return_task(task.id)
except Exception as e:
    task.result = f"{type(e).__name__}: {e!s}"
    task.set_state(TaskState.FAILED)
    await self._channel.return_task(task.id)
finally:
    self._active_task_ids.discard(task.id)
```

**Flow:** loop reaps done asyncio.Tasks first (awaiting each to surface exceptions as logs) → 1s-timeout blocking claim → spawn processor without awaiting → TimeoutError just continues (0.1s sleep only when nothing is running). Stop (`Worker.stop` :213-230) cancels running processors FIRST, clears the set, then flips `_running`; the listener's tail `asyncio.gather(*running_tasks, return_exceptions=True)` waits out survivors. Double-return protection lives channel-side (`return_task` no-ops when already RETURNED), so the except+normal paths can both fire safely.
**Invariant:** EVERY path through `_process_single_task` ends in `return_task` — a worker crash must still hand the task back or the supervisor's in-flight counter never reaches zero. Exceptions are converted into `Task.result = "Type: msg"` strings, not raised.
**Probe:** `grep -c 'return_task' camel/societies/workforce/worker.py` → 2; `grep -n 'timeout=1.0' camel/societies/workforce/worker.py` → 1 hit at :174.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "Worker _process_single_task return_task running_tasks", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt claim→spawn→guaranteed-return with exception-to-result-string conversion. Adapt timeout values. Omit `check_if_running` retry semantics (utils.py :734-839 — a separate state-gate decorator) unless porting lifecycle guards.
