<!-- capsule-v2 -->
# Timed-attempt observer contract — How does the engine expose node-attempt lifecycle (start/progress/finish) to external observers without letting observer failures break execution?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** A server needs per-node attempt telemetry (which attempt, when it started/progressed/finished, why) without coupling the execution kernel to any storage — what is the observer contract and how is progress emission kept bounded?

## One frozen context per attempt; small event wrappers reference it; dispatch is fail-open
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_retry.py:_AttemptContext` (:87-107), `_AttemptEvent` (:110-125), `_IdleProgressCallbackHandler` (:274-312), `_start_timed_attempt` (:343-366), `_finish_timed_attempt` (:370-390), `_dispatch_observer` (:407-414); rate limit in `_TimedAttemptScope.touch` (:195-209).
**Signature:** observer = `Callable[[_AttemptEvent], None]` stored under configurable key `CONFIG_KEY_TIMED_ATTEMPT_OBSERVER`; `_AttemptEvent(context: _AttemptContext, event: Literal["start","progress","finish"], progress_at=None, finished_at=None, status: Literal["success","error"]|None, error_type=None, error_message=None)`; `_AttemptContext(task_id, task_name, attempt, run_id, thread_id, checkpoint_ns, started_at, run_timeout_secs, idle_timeout_secs, refresh_on)` (NamedTuple, frozen by construction).
**Data Shape:** The context is built ONCE at attempt start and referenced (not copied) by every event for that attempt — per-event allocation is just the small wrapper. `attempt` comes from `execution_info.node_attempt` (1-indexed execution count). Both classes are deliberately underscore-prefixed but part of an internal observer contract consumed by langgraph-server, which imports them by this exact path.

### Decisive source
```python
def _dispatch_observer(callback: Callable[[_AttemptEvent], None], event: _AttemptEvent) -> None:
    try:
        callback(event)
    except Exception:
        logger.warning("Timed attempt observer failed", exc_info=True)
```
```python
    def touch(self) -> None:
        now = time.monotonic()
        self._last_progress = now
        if self._on_progress is None:
            return
        # Best-effort rate limit: a benign race may emit a duplicate progress
        # event under heavy concurrency, which observers must already tolerate
        if now - self._last_progress_emit < self._progress_min_interval:
            return
        self._last_progress_emit = now
        self._on_progress()
```

**Flow:** Each retry-loop iteration calls `_start_timed_attempt`, which returns `None` when no observer is configured (zero overhead path), else builds the context and emits `start`. Every progress touch inside the timed scope passes the rate-limit gate (`progress_min_interval = idle_timeout / 4`, set at scope construction) before emitting `progress`. On exit, `_finish_timed_attempt` emits `finish` with `status="error"` only for real errors — ParentCommand and bubble-up are treated as non-error finishes (pinned by tests) — and this happens BEFORE retry backoff, BEFORE the error handler's own attempt starts, and BEFORE the final raise on exhaustion. Observer exceptions are caught and logged ("Timed attempt observer failed") — the observer is strictly advisory. Progress scoping: `_IdleProgressCallbackHandler` touches the scope on all 19 LangChain callback methods, is injected via `config["callbacks"]` so inheritance scopes it to runs descended from the node's attempt (sibling nodes do not bleed in), holds the scope by weakref (a child manager outliving the attempt cannot keep the scope alive), and sets `run_inline = True` so progress is recorded in callback emission order.
**Invariant:** An observer failure never changes the attempt outcome; the context is immutable and shared across all events of one attempt; progress cadence is bounded to ~4 events per idle window; duplicate progress under race is tolerated by observers, not prevented by locks.
**Probe:** `python -m pytest "tests/test_retry.py::test_arun_with_retry_timeout_observer_tracks_attempts" "tests/test_retry.py::test_arun_with_retry_timeout_observer_emits_progress_on_heartbeat" "tests/test_retry.py::test_arun_with_retry_timeout_observer_treats_parent_command_as_non_error" "tests/test_retry.py::test_arun_with_retry_observer_emits_finish_before_retry_backoff" "tests/test_retry.py::test_arun_with_retry_observer_emits_finish_before_final_raise_on_exhaustion" -q` — 5 passed (attempt numbers [1,2] on start+finish, status ["error","success"], finish-before-backoff ordering, ParentCommand = non-error). Byte-exact: `grep -c "Timed attempt observer failed" libs/langgraph/langgraph/pregel/_retry.py` → 1; `grep -c "progress_min_interval=idle_timeout_s / 4" .../_retry.py` → 1; `grep -c "self._scope_ref = weakref.ref(scope)" .../_retry.py` → 1; `grep -c "on_custom_event = _touch" .../_retry.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "_IdleProgressCallbackHandler CONFIG_KEY_TIMED_ATTEMPT_OBSERVER _AttemptEvent observer", limit: 8 });
```

## Verdict
Adopt the frozen-context + small-event-wrapper allocation pattern, the fail-open dispatch (catch-all + warning, never propagate), the no-observer zero-overhead early return, and the lock-free rate-limited progress gate with duplicate tolerance. Adopt the callback-inheritance scoping + weakref hold if your host has a callback system; otherwise inject the progress source directly. Adapt the event vocabulary to your telemetry schema; keep the "finish before backoff / before error handler / before final raise" ordering — consumers rely on it to attribute retries. Omit heartbeat-only refresh unless callers need strict manual accounting.
