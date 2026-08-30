<!-- capsule-v2 -->
# UUIDv7 monotonic polyfill — 42-bit counter, clock-regression bump, overflow reseed

## Source / Question
`pydantic_ai_slim/pydantic_ai/_uuid.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you generate time-sortable IDs that are strictly monotonic within a millisecond AND survive a backwards system-clock step, per RFC 9562 Method 1? A porter will use plain `uuid.uuid4()` (loses sortability) or timestamp-only v7 (collides and goes backwards on clock regress).

## Path / Symbol
`_uuid.py` — `uuid7()` (:34–87), `_uuid7_get_counter_and_tail()` (:25–31), module globals `_last_timestamp_v7`/`_last_counter_v7`/`_lock_v7` (:17–19). CPython-3.14-matching polyfill; replace with stdlib once 3.14 is the floor.

## Signature
```python
def uuid7() -> uuid.UUID: ...
# layout: 48 unix_ts_ms | 4 version(0111) | 12 counter_hi | 2 variant | 30 counter_lo | 32 random
```

## Data Shape
Global state under a `threading.Lock`: last millisecond timestamp + a 42-bit counter whose MSB is forced to 0. The 32-bit random tail is regenerated EVERY uuid; the counter is seeded randomly at each new millisecond.

### Decisive source — the three regimes (:55–75)
```python
with _lock_v7:
    if _last_timestamp_v7 is None or timestamp_ms > _last_timestamp_v7:
        counter, tail = _uuid7_get_counter_and_tail()      # new ms: random seed
    else:
        if timestamp_ms < _last_timestamp_v7:
            timestamp_ms = _last_timestamp_v7 + 1          # clock went BACKWARDS: bump forward
        # advance the 42-bit counter
        counter = _last_counter_v7 + 1
        if counter > 0x3FF_FFFF_FFFF:
            # advance the 48-bit timestamp
            timestamp_ms += 1
            counter, tail = _uuid7_get_counter_and_tail()   # overflow: next ms, reseed
        else:
            tail = int.from_bytes(os.urandom(4), 'big')     # same ms: fresh tail only
    _last_timestamp_v7 = timestamp_ms
    _last_counter_v7 = counter
```

**Flow:** read clock → under lock pick regime: fresh-ms seed / same-ms increment / regression-bump / overflow-advance → write back globals → assemble int with version+variant flags OR'd in. Monotonicity comes from the shared counter; uniqueness-per-ms from the fresh 32-bit tail; sortability from the 48-bit timestamp field.

**Invariant:** Never emit a uuid whose (timestamp,counter) pair sorts before a previously issued one — even when the OS clock steps backwards. All global reads/writes happen inside one lock. Counter MSB stays 0 (RFC §6.2) so the 42-bit space halves but ordering stays well-defined.

**Probe:** `tests/test_uuid.py` — `test_uuid7_monotonic_within_millisecond` (:16), `test_uuid7_clock_regression` (:23), `test_uuid7_counter_overflow` (:43) pin all four regimes.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'uuid7 monotonicity counter'
```

## Verdict
**Adopt** verbatim for any host needing sortable event/run ids (message stores, span grouping) on Python <3.14. **Adopt** the lock discipline even in single-threaded hosts — asyncio task interleaving between the clock read and the counter write breaks monotonicity otherwise. **Omit** nothing; drop the module entirely once your floor is 3.14 (`uuid.uuid7()`).
