<!-- capsule-v2 -->

# Subscriber replay backfill window — How does a reconnecting event consumer recover everything it missed without a persistent cursor?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** What server-side replay window must a reconnecting websocket subscriber request so no event is lost across a disconnect?

## A rolling now-minus-overlap cursor, advanced only by delivered events, sent as `since` on every reconnect

**Path/Symbol:** `src/prefect/events/clients.py:PrefectEventSubscriber (693-936)` — `_reconnect` backfill block (835-851), `__anext__` cursor advance (899-904). Graph caveat: `_backfill_since` is an annotation-only attribute — NO graph Variable node exists; anchor on the class row (`PrefectEventSubscriber Class 693-936`) and read source directly.

**Signature:** `_backfill_since: Optional[DateTime]`; set in `_reconnect()`, advanced in `__anext__()`.

**Data Shape:** cursor starts at `now("UTC") - timedelta(minutes=1)` on first connect; per-event candidate is `event.occurred - timedelta(minutes=1)`.

### Decisive source
```python
# _reconnect, after auth handshake succeeds:
current_time = prefect.types._datetime.now("UTC")
if self._backfill_since is None:
    self._backfill_since = current_time - timedelta(minutes=1)

self._filter.occurred = EventOccurredFilter(
    since=self._backfill_since,
    until=current_time + timedelta(days=365),
)
filter_message = {"type": "filter", "filter": self._filter.model_dump(mode="json")}
await self._websocket.send(orjson.dumps(filter_message).decode())

# __anext__, for each event about to be returned:
replay_since = event.occurred - timedelta(minutes=1)
if (self._backfill_since is None or replay_since > self._backfill_since):
    self._backfill_since = replay_since
```

**Flow:** every successful (re)connect sends a filter whose `since` is the last-known cursor, so the SERVER replays everything newer than it — including events emitted during the disconnect. The client advances its own cursor only when an event is actually DELIVERED (monotonic max), never on connect time, so clock skew between reconnects cannot skip ahead past undelivered events. The ≥1-minute overlap around every boundary guarantees the replay re-covers events near the cut; duplicates that overlap produces are dropped by id dedup (see `subscriber-seen-id-dedup`).

**Invariant:** (1) Cursor advances are driven by delivery, not by wall-clock — a slow consumer can never have its cursor pass an unsent event. (2) The overlap window (1 minute here) must exceed worst-case redelivery tolerance and pairs with id-dedup; one without the other either loses or double-yields events. (3) `until=now+365d` makes the filter open-ended forward. Direct test pins the property: after a hard disconnect and a monkey-patched 2-minute time jump, the reconnect filter's `occurred.since <= last delivered event.occurred`.

**Probe:** direct test `tests/events/client/test_events_subscriber.py:301-334 test_subscriber_retains_replay_cursor_across_long_reconnect` — asserts `recorder.filter.occurred.since <= example_event_1.occurred` after `hard_disconnect_after = example_event_1.id` and a +2 min clock jump; companion `:275-298 test_subscriber_reconnects_on_hard_disconnects` shows both events still delivered across the reconnect (`recorder.connections == 2`).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^PrefectEventSubscriber$", "limit": 3}'
```
(observed rank-1: `PrefectEventSubscriber Class src/prefect/events/clients.py 693-936`; note `name_pattern "_backfill_since"` observed total: 0 — annotation-only attrs are not graph nodes.)

## Verdict
Adopt delivery-driven rolling cursors with server-side replay + bounded overlap for any resumable stream; adapt the window to your ordering/dup tolerance; omit Prefect's specific filter message schema.
