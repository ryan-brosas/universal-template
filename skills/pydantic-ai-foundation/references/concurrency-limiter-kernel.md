<!-- capsule-v2 -->
# Concurrency limiter kernel — shared slots, backpressure, and the check-and-register race

## Source / Question
`pydantic_ai_slim/pydantic_ai/concurrency.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you share one concurrency budget across many models/agents AND apply queue-depth backpressure without a race that lets N tasks all pass the queue check before any of them starts waiting? A porter will check `_waiting_count` without a lock and ship a racy limiter.

## Path / Symbol
`concurrency.py` — `ConcurrencyLimiter` (:95–247), `AbstractConcurrencyLimiter` (:35–74), `ConcurrencyLimit` dataclass (:77–92), `get_concurrency_context` (:277–294), `normalize_to_limiter` (:297–317).

## Signature
```python
class ConcurrencyLimiter(AbstractConcurrencyLimiter):
    def __init__(self, max_running: int, *, max_queued: int | None = None,
                 name: str | None = None, tracer: Tracer | None = None): ...
    async def acquire(self, source: str) -> None: ...
    def release(self) -> None: ...
def get_concurrency_context(limiter, source='unnamed') -> AbstractAsyncContextManager[None]
def normalize_to_limiter(limit: AnyConcurrencyLimit, *, name=None) -> AbstractConcurrencyLimiter | None
```

## Data Shape
`AnyConcurrencyLimit = 'int | ConcurrencyLimit | AbstractConcurrencyLimiter | None'`. An `int` is a bare limit with unlimited queue; `ConcurrencyLimit(max_running, max_queued)` adds backpressure; a pre-built limiter instance is shared as-is across models/agents; `None` means no limiting. Construction validates eagerly (`max_running >= 1`, `max_queued >= 0`) via `__post_init__`/`_validate_max_running`.

### Decisive source — the atomic check-and-register window (:200–243)
```python
# Try to acquire immediately without blocking
try:
    self._limiter.acquire_nowait()
    return
except anyio.WouldBlock:
    pass

# We need to wait - atomically check queue limits and register ourselves as waiting
# This prevents a race condition where multiple tasks could pass the check before
# any of them actually start waiting on the limiter
async with self._queue_lock:
    if self._max_queued is not None and self._waiting_count >= self._max_queued:
        raise ConcurrencyLimitExceeded(...)
    # Register ourselves as waiting before releasing the lock
    self._waiting_count += 1

try:
    ...
    await self._limiter.acquire()
finally:
    # We're no longer waiting (either we acquired or we were cancelled)
    self._waiting_count -= 1
```

**Flow:** `acquire_nowait()` fast path → on WouldBlock, take an `anyio.Lock`, check `_waiting_count >= max_queued` (raise `ConcurrencyLimitExceeded` naming `self._name or source`), register +1 under the SAME lock → release lock → open an OTel span ("waiting for {name|source} concurrency") around the blocking `await acquire()` → `finally` decrements the counter even on cancellation. `release()` delegates to the underlying `anyio.CapacityLimiter.release()`. `get_concurrency_context(None)` returns a no-op CM so callers never branch.

**Invariant:** The queue-limit check and the waiting-counter increment must happen inside ONE critical section; the decrement must be in `finally` so cancellation cannot leak a phantom waiter. Fast-path acquisitions never touch `_waiting_count`.

**Probe:** `tests/test_concurrency.py::test_backpressure_race_condition` (:142) pins exactly this race; `test_backpressure_raises` (:116) pins the rejection; `TestConcurrencyLimitedModel.test_shared_limiter_limits_across_models` (:410) pins cross-model sharing of one limiter instance.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'ConcurrencyLimiter acquire_nowait _queue_lock _waiting_count'
```

## Verdict
**Adopt** the whole kernel verbatim for any multi-agent host: eager validation, `None`→no-op CM, shared-limiter identity semantics, and the locked check-and-register ladder. **Adapt** the span attributes to your telemetry vocabulary; swap `anyio.CapacityLimiter` for your runtime's primitive if needed but keep the two-phase (nowait → registered-wait) shape. **Omit** nothing here — the module is 316 lines and every line carries the contract.
