<!-- capsule-v2 -->
# Supervisor listen loop — How does a coordinator node drive a whole task tree to completion while staying pause/stop/skip responsive?

**Source:** CAMEL-AI/camel Apache-2.0 `master@13dc7a7d`; Codebase Memory `ext-camel`. **Question:** What is the exact control-flow order of the supervisor's main loop — flags, decomposition, timeout, and per-state handling?

## One loop, five gates, checked in fixed order
**Path/Symbol:** `camel/societies/workforce/workforce.py:Workforce._listen_to_channel` (:5282-5802).
**Signature:** `async def _listen_to_channel(self) -> None` (started via `start()` :5822 after spawning child listeners with `asyncio.create_task(child.start())`).
**Data Shape:** Consumes `_pending_tasks: Deque[Task]`, `_in_flight_tasks: int`, `_pause_event: asyncio.Event` (set = running), `_stop_requested/_skip_requested: bool`; exits into `WorkforceState.{STOPPED, IDLE}`.

### Decisive source
```python
while (self._task is None or self._pending_tasks
        or self._in_flight_tasks > 0) and not self._stop_requested:
    try:
        await self._pause_event.wait()          # gate 1: pause
        if self._stop_requested: break          # gate 2: stop
        if self._skip_requested: ...continue    # gate 3: skip current queue
        if self._pending_tasks and self._in_flight_tasks == 0:
            if self._pending_tasks[0].additional_info.get('_needs_decomposition'):
                ... await self.handle_decompose_append_task(...)  # gate 4
        returned_task = await self._get_returned_task()           # gate 5
```

**Flow:** post ready tasks once up front (:5292) → each iteration re-checks pause → stop → skip → pending-decomposition flag (`_needs_decomposition` flipped to False BEFORE attempting, so failure cannot re-decompose forever) → throttled snapshot every `snapshot_interval=30.0`s → blocking `_get_returned_task()` wrapped by `asyncio.wait_for(task_timeout_seconds default TASK_TIMEOUT_SECONDS=600.0)`; TimeoutError breaks the loop only when tasks are actually in flight, else posts and continues → dispatch on `returned_task.state`: DONE (insufficient-result veto → FAILED path; quality evaluation when recovery strategies enabled; retry-limit escape hatch treats low quality as completed at `max(1, max_retries-1)`), FAILED (`_handle_failed_task` returns halt?), OPEN (TODO no-op), else ValueError. Outer `except Exception` decrements the in-flight counter ("unknown" id) and continues. Final state: STOPPED vs IDLE + AllTasksCompletedEvent; `self.stop()` always runs.
**Invariant:** The loop exits ONLY via `not stop_requested` and empty work (`no pending AND in_flight==0`) — every early `continue` must keep counters consistent or the workforce hangs; that is why the exception handler decrements in-flight before continuing.
**Probe:** `grep -c '_needs_decomposition' camel/societies/workforce/workforce.py` → 9 (loop gate :5334/:5342 plus add_task/reorder/resume/skip bookkeeping sites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-camel", query: "_listen_to_channel supervisor loop pause skip decompose", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered-gates loop shape and the timeout-with-inflight-check as the skeleton of any supervisor. Adapt gate bodies to host semantics. Omit the snapshot throttle unless you implement `save_snapshot`.
