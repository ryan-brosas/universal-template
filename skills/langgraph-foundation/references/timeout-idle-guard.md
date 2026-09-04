<!-- capsule-v2 -->
# Timeout idle guard — How do async nodes get run/idle timeouts where streaming progress slides the idle window?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** A long LLM stream must not trip an idle timeout just because tokens are slow-but-continuous — how is "progress" defined, and how does a timeout kill a running node cleanly?

## A watchdog race around a background task; the idle window slides on every touch
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_retry.py:_TimedAttemptScope` (:128-271), `_arun_with_timeout` (:422-517), `_ResolvedTimeout` (:63-84); sync rejection `libs/langgraph/langgraph/_internal/_timeout.py` (:7-10).
**Signature:** `TimeoutPolicy(run_timeout, idle_timeout, refresh_on: "auto" | "heartbeat")`; `_TimedAttemptScope(on_progress=None, progress_min_interval=0.0, refresh_on=None)` with `wrap_config(config) -> config`, `touch()`, `close()`, `await wait_for_idle_timeout(idle_timeout_s)`.
**Data Shape:** Progress sources under `refresh_on="auto"`: guarded channel writes (`CONFIG_KEY_SEND`), stream chunks (`CONFIG_KEY_STREAM`), child-task scheduling (`CONFIG_KEY_CALL`), runtime stream-writer calls, yielded stream chunks, and any LangChain callback event (via `_IdleProgressCallbackHandler`, inherited through `config["callbacks"]` so sibling nodes do not bleed in). Under `"heartbeat"`, only explicit `runtime.heartbeat()` counts.

### Decisive source
```python
    async def wait_for_idle_timeout(self, idle_timeout_s: float) -> None:
        while True:
            with self._lock:
                if not self._active:
                    return
                remaining = self._last_progress + idle_timeout_s - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError
            await asyncio.sleep(remaining)
```

**Flow:** `_arun_with_timeout` runs the proc in a background task plus up to two watchdogs (idle via `scope.wait_for_idle_timeout`, run via sleep-then-raise) under `asyncio.wait(FIRST_COMPLETED)`. The idle watchdog sleeps exactly `remaining` each wake and re-measures under the lock, so every `touch()` slides the deadline — a continuous token stream never times out while a dead one does within one idle window. On watchdog win: `scope.close()` (all guards become no-ops / raise CancelledError), `task.writes.clear()` (a killed attempt leaves no partial writes), cancel the background task with a drain callback, and raise `NodeTimeoutError(task.name, elapsed, kind="idle"|"run")`. On task win, watchdogs are cancelled with their TimeoutError suppressed. Guard locking is deliberate: `_guard_send`/`_guard_stream_writer` hold the lock around the active-check but call out unlocked (serialized with `close()` so cancelled tasks cannot persist writes past the boundary); `_guard_call`/`_guard_stream` hold no lock at all (event-loop-only paths); `touch()` is lock-free by design (coarse timeout vs scheduler race accepted). Sync targets are rejected up front — "sync Python execution cannot be safely cancelled in-process" — because in-process cancellation of blocking code is unsound.
**Invariant:** An attempt either completes fully (writes intact) or is killed with zero writes; the idle clock measures time since last observable progress, not wall time; progress emission to observers is rate-limited to ~4 events per idle window (`progress_min_interval = idle_timeout / 4`).
**Probe:** `python -m pytest "tests/test_retry.py::test_idle_timeout_guard_call_does_not_hold_scope_lock" "tests/test_retry.py::test_idle_timeout_guard_stream_does_not_hold_scope_lock" "tests/test_retry.py::test_idle_timeout_guard_stream_writer_does_not_hold_scope_lock" "tests/test_retry.py::test_idle_timeout_resets_on_message_stream_callbacks" -q` — all four pass (guards call out unlocked; a 0.15s idle timeout survives a slow token stream because message callbacks reset the clock). Byte-exact: `grep -c 'remaining = self._last_progress + idle_timeout_s - time.monotonic()' libs/langgraph/langgraph/pregel/_retry.py` → 1; `grep -c 'cannot be safely cancelled in-process' libs/langgraph/langgraph/_internal/_timeout.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "_TimedAttemptScope idle timeout guard", limit: 8 });
```

## Verdict
Adopt the watchdog-race shape for any cancellable async unit: background work + FIRST_COMPLETED race against deadline tasks, kill path clears partial effects before raising a typed timeout error. Define "progress" as your host's observable side effects (emissions, child scheduling, callbacks) and slide the window on each; keep the kill-path write-clearing invariant or you will checkpoint half-finished attempts. Omit the dual refresh modes unless callers need strict heartbeat-only accounting; start with auto.
