<!-- capsule-v2 -->
# Construction singleflight — why must concurrent first-uses of one connector share ONE instance instead of each building its own?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Three call sites lazily build connectors; without coordination, what breaks and what is the minimal correct lock shape?

## Module-global per-key asyncio.Lock with setdefault atomicity
**Path/Symbol:** `backend/python/app/connectors/core/base/connector/instance_lock.py` (whole file, 29L); consumers: streaming router + two event-service paths.
**Signature:** `def connector_init_lock(connector_id: str) -> asyncio.Lock` — `setdefault` between miss and insert.
**Data Shape:** `_init_locks: dict[str, asyncio.Lock]`; the docstring documents the failure it prevents: graph reads + `init()` + live connection test all happen before map-store, so racers each hold a full built instance.

### Decisive source
```python
lock = _init_locks.get(connector_id)
if lock is None:
    lock = _init_locks.setdefault(connector_id, asyncio.Lock())
return lock

# module docstring: "Without a shared lock every concurrent caller misses the same
# check and builds its own instance ... so the connector's configured rate limit is
# multiplied by the number of racers and a 429 seen by one instance pauses none of
# the others."
```

**Flow:** caller checks instance cache → miss ⇒ acquire `connector_init_lock(id)` → re-check inside lock (double-checked) → build via factory (`create_connector` binds org onto the entities processor) → store → release → later callers hit cache. Losers of the race get the winner's stored instance.
**Invariant:** Lock creation itself must be atomic — any await between dict-miss and insert lets two callers hold DIFFERENT locks for the same key (the bug this 29-line module exists to kill). The real damage is not duplicate CPU but duplicated RATE LIMITS: N instances = N× upstream QPS and independent backoff states, so resilience silently degrades under concurrency.
**Probe:** `grep -c '_init_locks.setdefault' app/connectors/core/base/connector/instance_lock.py` → `1`; suite `tests/unit/connectors/core/test_instance_lock.py` (7 tests) GREEN in battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "connector_init_lock singleflight", limit: 3 });
```
**Verdict:** Adopt verbatim (29 lines, zero deps); adapt only if host lacks asyncio. Pair with any lazy-construction cache whose builders are expensive AND rate-limit-carrying.
