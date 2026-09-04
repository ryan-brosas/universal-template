<!-- capsule-v2 -->

# Subscriber seen-id dedup — How do you absorb replayed duplicates from a backfilling event stream cheaply?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** What dedup structure makes server-side replay safe without unbounded client memory?

## TTLCache of seen event ids, checked before yield — bounded memory, self-expiring overlap

**Path/Symbol:** `src/prefect/events/clients.py` — constants (689-690), `_seen_events` init (751), check-before-yield in `__anext__` (896-898). Retrieve anchor: `SEEN_EVENTS_SIZE Variable 689-689`.

**Signature:** `_seen_events: MutableMapping[UUID, bool] = TTLCache(maxsize=SEEN_EVENTS_SIZE, ttl=SEEN_EVENTS_TTL)`.

**Data Shape:** `SEEN_EVENTS_SIZE = 500_000`, `SEEN_EVENTS_TTL = 120` (seconds); keys are event UUIDs, values are throwaway `True`.

### Decisive source
```python
SEEN_EVENTS_SIZE = 500_000
SEEN_EVENTS_TTL = 120
...
self._seen_events = TTLCache(maxsize=SEEN_EVENTS_SIZE, ttl=SEEN_EVENTS_TTL)
...
# __anext__ inner loop:
message = orjson.loads(await self._websocket.recv())
event: Event = Event.model_validate(message["event"])

if event.id in self._seen_events:
    continue                      # replayed duplicate — silently skipped
self._seen_events[event.id] = True
```

**Flow:** the backfill window (see `subscriber-replay-backfill-window`) deliberately re-sends events near every reconnect boundary. The subscriber records each delivered id BEFORE returning it and skips ids already present, so replayed events never reach the consumer twice. The cache is time- and size-bounded: entries expire after 120 s (far longer than any reconnect gap the overlap window covers) and at 500k ids it caps memory even against a hostile or broken server that resends ancient events.

**Invariant:** (1) Dedup is by EVENT ID, not by content — identical payloads with different ids both deliver; one id redelivered never yields twice within TTL. (2) Marking happens before yield, so a duplicate arriving while the first copy's handler is still running is still suppressed. (3) Bounded TTL means dedup is only valid for the overlap horizon; a reconnect gap longer than TTL can legitimately re-deliver old events — the window and TTL must be chosen together.

**Probe:** direct test `tests/events/client/test_events_subscriber.py:421-439 test_subscriber_skips_duplicate_events` — puppeteer emits `[example_event_1, example_event_1, example_event_2]`; consumer yields exactly `[example_event_1, example_event_2]`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "SEEN_EVENTS_SIZE", "limit": 3}'
```
(observed rank-1 line-exact: `SEEN_EVENTS_SIZE Variable src/prefect/events/clients.py 689-689`)

## Verdict
Adopt id-keyed TTL dedup ahead of any replay-based delivery guarantee; adapt size/TTL to your stream rate and overlap window (keep TTL ≥ overlap + reconnect latency); omit the specific cachetools dependency if your host has an equivalent bounded map.
