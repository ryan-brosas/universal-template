<!-- capsule-v2 -->
# coordinator-fsm-watchdog — Who owns cancellation for one app execution attempt, and when does the watchdog fire?

**Source:** dify Apache-2.0 `main@8bdf702f`; Codebase Memory `ext-dify`. **Question:** How do user stops, timeouts, and pause/resume coordinate into one non-racy abort path?

## Attempt-scoped state machine with cancel-before-callback watchdog
**Path/Symbol:** `api/core/app/apps/execution_coordinator.py:AppExecutionCoordinator` (:70-213); enum `AppExecutionState` (:17-21).
**Signature:** `__init__(*, task_id, on_timeout, timeout_seconds=None)`; `start_watchdog()`; `mark_paused()`; `mark_terminal()`; `listener_closed(*, segment_completed)`; `request_abort(reason) -> bool`.
**Data Shape:** States RUNNING→{PAUSED|ABORTING|TERMINAL}; `_abort_sent` latch; daemon `threading.Timer` watchdog; every mutation under one `threading.Lock`; timeout defaults to `dify_config.APP_MAX_EXECUTION_TIME`.

### Decisive source
```python
def start_watchdog(self) -> None:
    watchdog: threading.Timer | None = None
    run_immediately = False
    with self._lock:
        if self._watchdog_started or self._state is not AppExecutionState.RUNNING:
            return
        self._watchdog_started = True
        if self._timeout_seconds <= 0:
            run_immediately = True
        else:
            watchdog = threading.Timer(self._timeout_seconds, self._handle_timeout)
            watchdog.daemon = True
            self._watchdog = watchdog
    if run_immediately:
        self._handle_timeout()
    elif watchdog is not None:
        watchdog.start()

def request_abort(self, reason: str) -> bool:
    watchdog: threading.Timer | None = None
    with self._lock:
        if self._state is not AppExecutionState.RUNNING or self._abort_sent:
            return False
        self._abort_sent = True
        self._state = AppExecutionState.ABORTING
        watchdog = self._detach_watchdog_locked()
    if watchdog is not None:
        watchdog.cancel()          # CANCEL BEFORE callback work, outside the lock
    ...
    self._abort_execution(reason)  # stop flag + GraphEngine stop command
    return True
```

**Flow:** RUNNING (watchdog armed at first `listen()`); timeout fires → `request_abort` → ABORTING → set Redis stop flag + engine stop command → publish timeout stop event. Pause/terminal transitions detach and cancel the pending watchdog first, so a paused run can never be aborted by its own stale timer.
**Invariant:** Only a RUNNING attempt can transition; the watchdog is cancelled BEFORE any callback executes and outside the lock (lock-held callbacks would deadlock); `_abort_sent` makes abort idempotent — second callers get `False` and never double-publish.
**Probe:** `api/tests/unit_tests/core/app/apps/test_execution_coordinator.py::test_pausing_started_attempt_cancels_watchdog` (pause after start ⇒ `watchdog.start()` AND `watchdog.cancel()` called once each, state PAUSED).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-dify", query: "AppExecutionCoordinator mark_paused mark_terminal state transitions", limit: 10 });
```

## Verdict
Adopt the FSM + lock/cancel-before-callback discipline wholesale — it is host-independent. Adapt the timeout source (`APP_MAX_EXECUTION_TIME`) and the two abort sinks (Redis flag, GraphEngineManager command). Omit nothing here; the class has no Dify-only coupling beyond those two sinks. Direct tests cover all four transitions plus failure paths (10 tests, executed green via repo venv pytest 9.x: 19 passed in the coordinator/channels/tasks battery).
