<!-- capsule-v2 -->

# Sync/Async waiter primitives — How do you route work back to a thread or loop that is blocked waiting on a call?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect` (graph not connected this pass — direct source/test reads; see work record). **Question:** What is the primitive beneath `from_async`/`from_sync` that lets a worker thread send callbacks back to the waiting caller's thread/loop while it blocks?

## A thread-keyed waiter registry plus a callback queue drained during the wait, with cancel-wiring that bounds waiting to the parent call

**Path/Symbol:** `src/prefect/_internal/concurrency/waiters.py:Waiter (43-88)`, `SyncWaiter (91-153)`, `AsyncWaiter (156-276)`, `_WAITERS_BY_THREAD`/`add_waiter_for_thread` (28-40). This is the layer P2's waiter twins (`waiter-completion-event-race-ladder`) build on for cross-thread Event creation.

**Signature:** `SyncWaiter.wait() -> Call[T]`; `async def AsyncWaiter.wait() -> Call[T]`; `submit(call: Call[T]) -> Call[T]`; `add_done_callback(callback: Call[Any]) -> None`.

**Data Shape:** `_WAITERS_BY_THREAD: WeakKeyDictionary[threading.Thread, deque[Waiter]]` — worker threads look up the owner thread's pending waiters; weak keys drop dead threads automatically. Sync drain uses `queue.Queue` + `threading.Event`; async drain uses a lazily-created `asyncio.Queue` owned by the loop that calls `wait()`.

### Decisive source
```python
# SyncWaiter.wait — poison pill + done-event both registered as done-callbacks:
self._call.future.add_done_callback(lambda _: self._queue.put_nowait(None))
self._call.future.add_done_callback(lambda _: self._done_event.set())
with self._handle_done_callbacks():          # finally: run done callbacks
    self._handle_waiting_callbacks()          # drain queue until None
    self._done_event.wait()                   # then block until the call is done

# _handle_waiting_callbacks — the bound that keeps waiting honest:
callback = self._queue.get()
if callback is None: break
# Ensure that callbacks are cancelled if the parent call is cancelled so
# waiting never runs longer than the call
self._call.future.add_cancel_callback(callback.future.cancel)
callback.run()

# AsyncWaiter.submit — loop ownership discipline:
if not self._queue:                          # no loop yet
    self._early_submissions.append(call)     # park in a plain list
    return call
call_soon_in_loop(self._loop, self._queue.put_nowait, call)  # only the owning loop touches the queue

# AsyncWaiter._signal_stop_waiting — never push after the drain finished:
if not self._done_waiting:
    call_soon_in_loop(self._loop, self._queue.put_nowait, None)
```

**Flow:** construction registers the waiter under the CURRENT thread in the weak-keyed registry. `wait()` first drains every callback submitted by other threads (each one cancel-wired to the parent future), then blocks on the done event; done callbacks run in a finally block afterwards, so they fire on completion, timeout/cancel, AND exception. AsyncWaiter defers loop+queue creation to `wait()` itself; submissions arriving before the loop exists park in `_early_submissions` and are resubmitted via `call_soon_in_loop` once the loop binds. Async callbacks returning awaitables are collected and `asyncio.gather`ed as a group (concurrent, not sequential), and each done callback runs inside `anyio.CancelScope(shield=True)` so cancellation cannot skip cleanup. A BaseException raised across the boundary never escapes `wait()` — it lands on the Call's future and done callbacks still run.

**Invariant:** (1) Waiting must be bounded by the parent call: every queued callback gets a cancel-callback wired to the parent future, or a slow callback can outlive the call it was sent to interrupt. (2) Done callbacks must run in a finally (and shielded in the async variant) — tests pin "the done callback should still be called on cancel" and "on exception". (3) An asyncio.Queue may only be touched from its owning loop: pre-loop submissions must park elsewhere and be resubmitted via `call_soon_in_loop`, and the stop signal must check `_done_waiting` before pushing or it can hit a dead loop. (4) The registry must be weak-keyed by thread or finished threads leak their waiter deques. (5) `submit`/`add_done_callback` on an already-done waiter raise RuntimeError — silent drops would hide ordering bugs.

**Probe:** direct tests `tests/_internal/concurrency/test_waiters.py`: `:60-72 test_async_waiter_early_submission` (submit before loop exists still executes); `:108-134 test_sync_waiter_timeout_in_worker_thread` (timeout → CancelledError on result, done callback still ran, wait returned < 2 s); `:240-263 test_async_waiter_timeout_in_worker_thread_mixed_sleeps` (one consistent deadline across sync+async parts); `:266-288 test_async_waiter_base_exception_in_worker_thread` ×6 parametrizations (BaseException/KeyboardInterrupt/SystemExit land on the future, wait() does not throw, done callback ran); `:330-348 test_sync_waiter_base_exception_in_worker_thread`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^(SyncWaiter|AsyncWaiter)$", "limit": 5}'
```
(expected rank-1/2: `SyncWaiter Class src/prefect/_internal/concurrency/waiters.py 91-153`, `AsyncWaiter Class ... 156-276`; graph was NOT connected in the mining session that authored this capsule — verify live before relying on line numbers.)

## Verdict
Adopt the thread-keyed weak registry + drain-then-block + cancel-wired callbacks + finally-run done callbacks for any cross-thread "send work back to the waiter" bridge; adopt the early-submission parking list and `_done_waiting` guard for the async variant. Adapt the Call/Future types to your host; omit Prefect's Portal base-class coupling.
