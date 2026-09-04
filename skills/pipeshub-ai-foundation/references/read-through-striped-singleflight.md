<!-- capsule-v2 -->
|# Read-through single-flight with striped locks — how do you collapse concurrent cache misses without an unbounded lock table?

## Fixed stripe array (crc32-keyed) instead of per-key locks; re-check INSIDE the lock; loader runs exactly once per miss cohort
**Path/Symbol:** `backend/python/app/services/cache/accessible_records_cache.py` :84–100 (`LOCK_STRIPES=1024` with the WHY comment :79–84), `_get_or_compute` :185–214, `_lock_for` :216–219 (`zlib.crc32(lock_key.encode()) % len(self._locks)` — NOT `hash()`, which is per-process seeded).
**Signature:** `lock_key = key if field is None else f"{key}#{field}"`; `async _get_or_compute(key, field, loader: Loader) -> dict[str,str]` with `Loader = Callable[[], Awaitable[dict[str, str]]]`.
**Data Shape:** tuple of asyncio.Lock fixed at construction; disabled/broken Redis short-circuits straight to `loader()` at THREE gates (entry, post-failed-read, post-lock-acquire).

### Decisive source
```python
# A failed read has already tripped the breaker. Every further Redis
# call in this same request would wait out its own timeout, so one
# outage cost three of them (read, re-read, write) on a single search.
if not self.enabled:
    return await loader()

lock_key = key if field is None else f"{key}#{field}"
async with lock:
    if not self.enabled:
        return await loader()
    # Another coroutine may have populated the entry while we queued.
    cached = await self._read(key, field)
    if cached is not None:
        return cached
    value = await loader()
    if self.enabled:                      # breaker may trip WHILE loading
        await self._write(key, field, value)
    return value

def _lock_for(self, lock_key):            # crc32 rather than hash()
    return self._locks[zlib.crc32(lock_key.encode()) % len(self._locks)]
```

**Flow:** enabled-check → read → (breaker tripped? live loader) → stripe-lock → double-check (enabled + re-read) → load → conditional write. The class docstring for LOCK_STRIPES records the failure it replaces: "A per-key table could only be trimmed of *unlocked* entries, so under enough concurrent misses on distinct keys it grew without limit."
**Invariant:** the lock array is bounded BY CONSTRUCTION; two unrelated keys sharing a stripe merely serialise their (already expensive) miss. The post-lock `enabled` check before `_write` prevents issuing new Redis calls after the read tripped the breaker mid-request ("Healthy on entry, dead by the time the loader returns").
**Probe:** `backend/python/tests/unit/services/cache/test_accessible_records_cache.py::TestSingleFlight::test_concurrent_misses_run_the_loader_once` (:217, gather×10 ⇒ len(calls)==1), `::test_lock_table_bounded_while_every_lock_is_held` (:259 — THE regression for the old table), `::test_same_key_maps_to_one_stripe_and_is_stable` (:280 cross-instance stability), `TestOutageCost::test_write_is_skipped_when_the_locked_read_trips_the_breaker` (:344).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "_lock_for LOCK_STRIPES get_or_compute", limit: 10 });
```

## Verdict
Adopt striped crc32 locking + double-checked read-through + the enabled-gated write; adapt stripe count to your concurrency profile; omit nothing else — pattern is host-portable wholesale. Direct tests ship upstream including the bounded-table regression.
