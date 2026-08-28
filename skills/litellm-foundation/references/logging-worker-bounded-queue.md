<!-- capsule-v2 -->
# LoggingWorker — bounded best-effort queue for fire-and-forget async callbacks

**Source:** litellm MIT `litellm_internal_staging@f005afa1460385a218be8ef1fdfa49998bf93523`; Codebase Memory `litellm` (MCP not connected at authoring time — direct source+test reading fallback, recorded in work record). **Question:** How does the background logging worker keep callback latency off the request path while guaranteeing the hot enqueue path never blocks, and what happens to queued work under backpressure, loop changes, and process exit?

## The worker core — bounded queue + semaphore + per-coroutine timeout
**Path/Symbol:** `litellm/litellm_core_utils/logging_worker.py` — `LoggingWorker` (:35-338), `GLOBAL_LOGGING_WORKER` (:524); knobs in `litellm/constants.py` (:475-484): `LOGGING_WORKER_CONCURRENCY=100`, `LOGGING_WORKER_MAX_QUEUE_SIZE=50_000`, `LOGGING_WORKER_MAX_TIME_PER_COROUTINE=20.0`, `LOGGING_WORKER_CLEAR_PERCENTAGE=50`, `MAX_ITERATIONS_TO_CLEAR_QUEUE=200`, `MAX_TIME_TO_CLEAR_QUEUE=5.0`, `LOGGING_WORKER_AGGRESSIVE_CLEAR_COOLDOWN_SECONDS=0.5` (all env-overridable).
**Signature:** `LoggingWorker(timeout: float = 20.0, max_queue_size: int = 50_000, concurrency: int = 100)`; `enqueue(coroutine: Coroutine) -> None`; `ensure_initialized_and_enqueue(async_coroutine) -> None`.
**Data Shape:** each queue item is a `LoggingTask` TypedDict `{coroutine, context}` — the contextvars.Context is captured at ENQUEUE time so callbacks run in the original request's context (trace_id/session_id survive the hop).

### Decisive source
```python
# logging_worker.py:148-153 — hot path never blocks
try:
    self._queue.put_nowait(task)
except asyncio.QueueFull:
    verbose_logger.exception("LoggingWorker queue is full")
    self._handle_queue_full(task)
...
# logging_worker.py:99-102 — per-coroutine timeout inside its captured context
await asyncio.wait_for(
    task["context"].run(asyncio.create_task, task["coroutine"]),
    timeout=self.timeout,
)
```

**Flow:** `start()` is idempotent and reinitializes queue/semaphore/worker when the running event loop changed (`_bound_loop` check — old-loop-bound objects are dropped). The single `_worker_loop` acquires the semaphore BEFORE dequeuing (prevents unbounded growth of waiting tasks), spawns one processing task per item tracked in `_running_tasks` with a done-callback discard; task-creation failure releases the semaphore to avoid deadlock. Each task runs via `context.run(create_task, coroutine)` wrapped in `wait_for(timeout)`; exceptions are logged, `task_done()` always runs, semaphore always released.
**Invariant:** Enqueue is non-blocking by contract — a full queue must degrade (drop-or-defer), never backpressure the request path. Context capture at enqueue (not at run) is what makes correlation ids correct across the hop.
**Probe:** `tests/test_litellm/litellm_core_utils/test_logging_worker.py` executed live at the pin → 12 passed (incl. `test_context_propagation`, `test_semaphore_concurrency_limit`, `test_event_loop_change_handling`).

## Backpressure — aggressive clear with cooldown vs delayed retry
**Path/Symbol:** `logging_worker.py` — `_handle_queue_full` (:187-199), `_should_start_aggressive_clear` (:155-174), `_calculate_retry_delay` (:201-219), `_schedule_delayed_enqueue_retry` (:221-236), `_extract_tasks_from_queue` (:255-279), `_aggressively_clear_queue_async` (:281-304), `_process_extracted_tasks` (:322-331).

### Decisive source
```python
# logging_worker.py:193-199 (abridged)
if self._should_start_aggressive_clear():
    self._mark_aggressive_clear_started()
    asyncio.create_task(self._aggressively_clear_queue_async(task))  # non-blocking
else:
    self._schedule_delayed_enqueue_retry(task)  # cooldown active or clear in progress
...
# logging_worker.py:210-216 — retry delay = remaining cooldown + max(50ms, 10% of cooldown)
remaining_cooldown: Final = max(0.0, COOLDOWN - time_since_last_clear)
return remaining_cooldown + max(0.05, COOLDOWN * 0.1)
```

**Flow:** on QueueFull: if no clear is in progress AND ≥0.5s since the last one, start an aggressive clear — extract CLEAR_PERCENTAGE (50%) of capacity from the head of the queue plus the new task, and process them concurrently with `asyncio.gather` WITHOUT the semaphore ("for maximum speed"), each still under the per-coroutine timeout; the in-progress flag resets in `finally`. Otherwise schedule a delayed retry after the remaining cooldown plus a small buffer, preserving the original context; a retry that still hits QueueFull recurses through `_handle_queue_full`. No event loop ⇒ drop the task (best-effort).
**Invariant:** The cooldown + in-progress pair bounds how often the O(queue) extraction runs; the delayed retry exists precisely so tasks are not silently dropped during the cooldown window. Clearing bypasses the semaphore deliberately — it is the emergency path.
**Probe:** same live suite — `test_queue_full_handling` (:187) and `test_aggressive_queue_clearing` (:355) both passed.

## Shutdown — stop, flush, and the atexit drain
**Path/Symbol:** `logging_worker.py` — `stop` (:340-360), `flush` (:362-373), `clear_queue` (:375-406), `_safe_log` (:408-446), `_flush_on_exit` (:448-520); registered via `atexit.register(self._flush_on_exit)` in `__init__` (:62).

### Decisive source
```python
# logging_worker.py:362-373 — flush waits on the unfinished-task counter, NOT empty()
async def flush(self) -> None:
    """``queue.join()`` blocks on the queue's unfinished-task counter ... ``queue.empty()``
    would return True in that window and cause us to skip the wait."""
    if self._queue is None:
        return
    await self._queue.join()
...
# logging_worker.py:483-484 — scope the suppression to just the drain window
previous_raise_exceptions: Final = logging.raiseExceptions
logging.raiseExceptions = False
```

**Flow:** `stop()` cancels every running task plus the worker loop and gathers with `return_exceptions=True`; `CancelledError` in the worker loop triggers `clear_queue()` (drain up to 200 items within 5s, awaiting each so coroutines are never left "never awaited"). `flush()` uses `queue.join()` because `empty()` races items that were dequeued but whose callback has not finished. The atexit handler creates a NEW event loop (the original is closed at exit), drains up to 200 items within 5s running coroutines directly via `run_until_complete` (not create_task — fresh loop context), scopes `logging.raiseExceptions=False` to just the drain window so other threads keep error reporting, and logs only through `_safe_log` which checks handler streams for closure before writing.
**Invariant:** Best-effort means "never break the user's program on exit": every shutdown path swallows errors, caps iterations AND wall time, and treats closed logging handlers as expected. join-not-empty is the correctness line for flush.
**Probe:** same live suite — `test_flush_on_exit_suppresses_closed_handler_errors`, `test_flush_on_exit_swallows_errors_and_drains_remaining`, `test_clear_queue_with_time_limit`, `test_worker_handles_cancellation_gracefully` all passed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "litellm",
  query: "LoggingWorker _handle_queue_full _aggressively_clear_queue_async _flush_on_exit",
  filePattern: "logging_worker.py", limit: 20 });
// → surfaces the class body (:35+), the backpressure ladder, and the atexit drain
```

## Verdict
Adopt the whole shape: bounded queue + semaphore-before-dequeue + per-coroutine wait_for, contextvars captured at enqueue, non-blocking put_nowait with the cooldown-gated aggressive clear (percentage-of-capacity extraction processed without the semaphore) vs delayed-retry fallback, join-not-empty flush, and the capped dual-limit (iterations + wall time) atexit drain on a fresh loop with scoped raiseExceptions suppression. Adapt the seven env-tunable constants to your latency budget; keep the best-effort error-swallowing posture on every shutdown path. Omit nothing structural — the file is 524 lines and every section above is load-bearing. Coverage caveat: none — the dedicated suite ran green at the pin.
