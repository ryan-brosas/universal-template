<!-- capsule-v2 -->
# Global rate limiter singleton — how does a per-pool delay become process-wide without deadlocking concurrency?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** Why is SCRAPER_RATE_LIMIT_DELAY enforced globally, and what is the exact lock discipline a porter must reproduce?

## GlobalRateLimiter + WorkerPool.throttle
**Path/Symbol:** `gpt_researcher/utils/rate_limiter.py:13-92` (singleton), `gpt_researcher/utils/workers.py:8-50` (`WorkerPool`, `throttle`).
**Signature:** `def __new__(cls)` singleton; `@classmethod def get_lock(cls)`; `async def wait_if_needed(self)`; `@asynccontextmanager async def throttle(self)`.
**Data Shape:** `_instance: ClassVar`, `_lock: ClassVar[asyncio.Lock]` created LAZILY inside async context; `rate_limit_delay: float` seconds (0 = unlimited); module-level `get_global_rate_limiter()` accessor.

### Decisive source
```python
async with self.semaphore:                 # pool-local concurrency seats
    global_limiter = get_global_rate_limiter()
    await global_limiter.wait_if_needed()  # GLOBAL timing across ALL pools
    yield
...
async with lock:
    time_since_last = current_time - self.last_request_time
    if time_since_last < self.rate_limit_delay:
        await asyncio.sleep(self.rate_limit_delay - time_since_last)
    self.last_request_time = time.time()
```

**Flow:** EVERY WorkerPool constructor calls `global_limiter.configure(rate_limit_delay)` — last pool to be built wins the shared config → each scrape acquires its pool's semaphore, then the global lock, sleeps the remainder, stamps time, and HOLDS ITS SEMAPHORE SEAT while yielding.
**Invariant:** two-level design exists because deep research spawns multiple researchers each owning pools — per-pool limits would multiply request rate by pool count. The class-level lock must be constructed in async context (an `asyncio.Lock` bound at import binds the wrong/no loop). Timestamp stamped AFTER sleeping so back-to-back waits chain correctly.
**Probe:** battery P06a-d GREEN (`_instance = super().__new__(cls)` ×1; `global_limiter.configure(rate_limit_delay)` ×1 in workers).
