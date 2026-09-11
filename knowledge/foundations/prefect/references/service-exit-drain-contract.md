<!-- capsule-v2 -->

# Dual exit-drain registration — Why does queued work need BOTH a loop-shutdown call and a private atexit hook?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** How does a background queue service flush pending items at process exit without deadlocking interpreter finalization?

## Stop is a poison pill; drain waits on the done event; exit uses TWO hooks

**Path/Symbol:** `src/prefect/_internal/concurrency/services.py:start (100-123)`, `_at_exit (125-126)`, `_stop (128-152)`, `drain (251-261)`, `_drain (232-249)`, `drain_all (263-298)`, `_main_loop stop check (183-205)`.

**Signature:** `drain(self, at_exit: bool = False) -> Union[bool, Awaitable[bool]]`; `drain_all(cls, timeout=None, at_exit=True)`; `_stop(self, at_exit=False)`.

**Data Shape:** `_stopped: bool` flag; sentinel item `None` in the queue; `asyncio.Event` done signal awaited cross-thread via `asyncio.run_coroutine_threadsafe`.

### Decisive source
```python
# start():
# Ensure that we wait for worker completion before loop thread shutdown
loop_thread.add_shutdown_call(create_call(self.drain))
# Stop at interpreter exit by default ... new threads cannot be spawned after
# the interpreter finalizes threads which happens _before_ the normal `atexit`
# hook is called ... https://github.com/python/cpython/issues/86813
threading._register_atexit(self._at_exit)

def _stop(self, at_exit: bool = False) -> None:
    if self._stopped:
        return
    with self._lock:
        self._remove_instance()
        self._stopped = True
        # Allow asyncio task to be garbage-collected. Its context may contain
        # references to all Prefect Task calls made during a flow run ... #10338.
        self._task = None
        self._queue.put_nowait(None)
```

**Flow:** drain() → `_stop()` removes instance from the registry FIRST (so no new sends find it), nulls the task ref (its context otherwise pins every Task call made during the run — leak), enqueues `None`; the main loop sees `item is None`, marks task_done, breaks; remaining queued items are still processed before the sentinel because FIFO; `_drain` then awaits `done_event`. In async contexts drain returns an awaitable; sync callers block on the future.

**Invariant:** (1) The registry removal precedes any wait — callers racing a drain get a FRESH instance instead of enqueueing into a dying one. (2) Exit flushing needs two hooks: the global loop's shutdown call handles normal teardown, but CPython finalizes threads BEFORE plain `atexit`, so handlers that spawn threads/HTTP clients must flush via private `threading._register_atexit`, which runs earlier. (3) During interpreter-exit drains, skip logging (`at_exit=True`) — the logging stack may already be torn down.

**Probe:** direct tests `tests/_internal/concurrency/test_services.py:285 test_drain_on_global_loop_shutdown`, `:295 test_drain_on_exit`, `:309 test_drain_on_exit_async_from_same_loop`, `:218 test_drain_safe_to_call_multiple_times`, `:234 test_drain_clears_asyncio_task` (`instance._task is None` after drain), `:320/:341 test_drain_all_timeout_{sync,async}`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^(drain|drain_all|_stop|_run|_new_instance)$", "limit": 8}'
```
(observed top kernel rows: `_QueueServiceBase._new_instance 324-338`, `_QueueServiceBase._run 158-181`, `_QueueServiceBase._stop 128-152`)

## Verdict
Adopt poison-pill stop + registry-first removal + dual shutdown/atexit registration with an earlier-than-atexit private hook for thread-spawning flushes; adapt hook names to your runtime; omit issue-10338 context-leak specifics beyond "null the task so its context can't pin run objects".
