<!-- capsule-v2 -->
# contextmanager_in_threadpool — Why must a sync yield-dependency's __exit__ run OUTSIDE the shared threadpool capacity?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** How is a synchronous `@contextmanager` dependency executed without deadlocking the anyio worker pool?

## Dedicated CapacityLimiter(1) for teardown
**Path/Symbol:** `fastapi/concurrency.py:contextmanager_in_threadpool` (17–41, whole module 41L); used by `fastapi/dependencies/utils.py:_solve_generator` (566–574).
**Signature:** `contextmanager_in_threadpool(cm: AbstractContextManager[_T]) -> AsyncGenerator[_T, None]` (asynccontextmanager-decorated generator function).
**Data Shape:** enter via `run_in_threadpool(cm.__enter__)` (shared default limiter); exit via `anyio.to_thread.run_sync(cm.__exit__, ..., limiter=exit_limiter)` with a FRESH `CapacityLimiter(1)` per call.

### Decisive source
```python
    # blocking __exit__ from running waiting on a free thread
    # can create race conditions/deadlocks if the context manager itself
    # has its own internal pool (e.g. a database connection pool)
    # to avoid this we let __exit__ run without a capacity limit
    # since we're creating a new limiter for each call, any non-zero limit
    # works (1 is arbitrary)
    exit_limiter = CapacityLimiter(1)
    try:
        yield await run_in_threadpool(cm.__enter__)
    except Exception as e:
        ok = bool(await anyio.to_thread.run_sync(
            cm.__exit__, type(e), e, e.__traceback__, limiter=exit_limiter))
        if not ok:
            raise e
    else:
        await anyio.to_thread.run_sync(
            cm.__exit__, None, None, None, limiter=exit_limiter)
```

**Flow:** the yielded value is produced by entering the CM in a worker thread → exception semantics mirror a real `with` block: `__exit__` receives the exception triple and its Falsey return RE-RAISES the original exception (`raise e`), truthy suppresses → clean path passes `(None, None, None)`.
**Invariant:** (1) The comment is the contract — teardown waiting on the DEFAULT pool's free token can deadlock when the CM's body holds that pool (DB pools sized to the same limiter); a private one-token limiter sidesteps capacity coupling entirely. (2) Suppression is honored: returning True from `__exit__` swallows the endpoint error by design, matching sync `with`. (3) Each call gets its OWN limiter — never hoist it to module scope or concurrent teardowns serialize globally.
**Probe:** exercised by every sync yield-dependency suite (`tests/test_dependency_contextmanager.py`, `tests/test_dependency_after_yield_raise.py`) — the observable boundary is teardown ordering + exception propagation through sync CMs.
