<!-- capsule-v2 -->
# Skip request handling — How does a supervisor abandon the current task queue and move to the next main task?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What does `_handle_skip_task` drain, count, and return so the listen loop can decide stop-vs-continue?

## Drain pending, remove from channel, treat as completed-with-skip
**Path/Symbol:** `camel/societies/workforce/workforce.py:Workforce._handle_skip_task` (:5164+) consumed at loop gate 3 (:5310-5318); in-flight decrement helper (:1500-1523).
**Signature:** `async def _handle_skip_task(self) -> bool` — True = no more main tasks ⇒ set stop.
**Data Shape:** iterates `self._pending_tasks` snapshot; per removed task calls `self._channel.remove_task(task.id)` + `self._decrement_in_flight_tasks(task.id, "skip request - removed from channel")` then `_handle_completed_task(task)`.

### Decisive source
```python
if self._skip_requested:
    should_stop = await self._handle_skip_task()
    if should_stop:
        self._stop_requested = True
        break
    self._skip_requested = False
    continue
```

**Flow:** skip flag set (thread-safely via `_async_skip_gracefully`, which also releases a paused loop) → loop's third gate consumes it → handler clears the pending deque, removing each posted packet from the channel so workers' atomic claims can't resurrect them, decrements the in-flight counter per removal (guarded >0 clamp), records each as completed for dependency bookkeeping → returns whether any main-task queue remains; empty ⇒ stop. Counter discipline mirrors the exception path — ANY exit that abandons posted tasks must decrement or the supervisor's `in_flight>0` liveness condition wedges.
**Invariant:** Skip is bookkeeping-honest: abandoned tasks are marked completed (not deleted silently) so dependents resolve deterministically instead of waiting forever.
**Probe:** `grep -c 'skip request - removed from channel' camel/societies/workforce/workforce.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "_handle_skip_task _decrement_in_flight_tasks remove_task", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt drain-with-bookkeeping for cooperative cancellation of queued work. Adapt "completed" semantics to your ledger. Omit main-task queueing (`add_task(as_subtask=False)` + `_needs_decomposition`) if you have no multi-main-task mode.
