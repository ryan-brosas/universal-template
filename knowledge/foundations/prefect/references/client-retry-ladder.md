<!-- capsule-v2 -->

# Client-side retry ladder — Where do delay lists clamp, when does AwaitingRetry beat Retrying, and what does can_retry swallow?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `ext-prefect`. **Question:** How does the CLIENT engine decide retry vs fail without server round-trips, and where would a porter get the delay arithmetic wrong?

## retries counter on engine, final-delay repeat, condition failure = no-retry

**Path/Symbol:** `src/prefect/task_engine.py:SyncTaskRunEngine.handle_retry (660-713)`, `can_retry (442-477)`; async twins `handle_retry (1286-1340)` / `can_retry (1054-1088)`; consumed by `handle_exception` (`715-728`) and `handle_timeout` (`730-743`) — timeouts RETRY like exceptions.

**Signature:** `handle_retry(exc_or_state: Exception | State[R]) -> bool`; `can_retry(exc_or_state) -> bool`.

**Data Shape:** `self.retries` counts ATTEMPTS ALREADY CONSUMED on the engine instance (server never sees it until state proposals). Delay source is `task.retry_delay_seconds`: scalar OR Sequence.

### Decisive source
```python
if self.retries < self.task.retries and self.can_retry(exc_or_state):
    if self.task.retry_delay_seconds:
        delay = (
            self.task.retry_delay_seconds[
                min(self.retries, len(self.task.retry_delay_seconds) - 1)
            ]  # repeat final delay value if attempts exceed specified delays
            if isinstance(self.task.retry_delay_seconds, Sequence)
            else self.task.retry_delay_seconds
        )
        new_state = AwaitingRetry(
            scheduled_time=prefect.types._datetime.now("UTC")
            + timedelta(seconds=delay)
        )
    else:
        new_state = Retrying()
    ...
    self.set_state(new_state, force=True)
    self.retries += 1
    return True
```

**Flow:** exception/timeout → handle_retry → gate `engine.retries < task.retries AND can_retry(...)` → delayed: AwaitingRetry(now+delay) else immediate Retrying → propose FORCE (a Failed→Retrying transition needs force since it's non-standard) → increment counter → caller loop re-enters `while engine.is_running(): wait_until_ready()` which sleeps out `scheduled_time` then proposes Running (name-based check `self.state.name == "AwaitingRetry"` decides Retrying-vs-Running proposal). Exhausted or condition-false ⇒ return False ⇒ handle_exception writes terminal Failed.

**Invariant:** (1) Delay-list indexing clamps with `min(self.retries, len(list)-1)` — attempts beyond the list REPEAT THE FINAL DELAY rather than IndexError; porters who index directly crash on attempt N+1. (2) `can_retry` wraps the user's `retry_condition_fn` in try/except returning False on ANY internal error — a buggy condition function disables retries instead of crashing the run; it also synthesizes the Failed state passed to the condition (`data=exc_or_state`) and bridges async conditions via `run_coro_as_sync`. (3) An explicitly returned FAILED STATE from user code flows through handle_success → handle_retry too (`isinstance(result, State) and result.is_failed()`), i.e. returning Failure is retryable by design.

**Probe:** `grep -c 'retry_delay_seconds\[' src/prefect/task_engine.py` → 2 (sync+async); `grep -c 'min(self.retries, len(self.task.retry_delay_seconds) - 1)' src/prefect/task_engine.py` → 2. Direct test: `tests/test_task_engine.py:410 test_task_ends_in_failed_after_retrying` (sync twin :783) plus delay-parse validation `tests/test_tasks.py:4778 TestTaskConstructorValidation.test_task_accepts_fractional_retry_delay_seconds`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-prefect", "query": "handle_retry task retries", "limit": 4}'
```

## Verdict
Adopt the clamp-and-repeat delay ladder and the condition-failure-disables-retry rule for any client-side retry budget; adapt state names to your state machine; omit the orchestration-API side of retry policies.
