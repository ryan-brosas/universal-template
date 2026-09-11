<!-- capsule-v2 -->

# Flow-run dual-stream fan-in — How do you interleave two independent live streams into one iterator without stranding either?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect` (graph not connected this pass — direct source/test reads; see work record). **Question:** When a UI must show BOTH logs and events for one run from two separate websocket subscriptions, how do you merge them into a single async iterator with correct termination?

## Two background consumers feed one queue; sentinels count stream deaths; exceptions travel as items; a straggler timeout bounds the tail

**Path/Symbol:** `src/prefect/events/subscribers.py:FlowRunSubscriber (26-210)` — `__aenter__` (94-115), `_is_terminal_event` (132-144), `__anext__` (152-172), `_consume_logs` (175-190), `_consume_events` (192-210). Adjudication note: state.md guessed "server-side distribution plane" — WRONG; this class composes the two CLIENT-side subscribers (`get_events_subscriber`, `get_logs_subscriber`) and is fully client-side.

**Signature:** `async def __anext__(self) -> Union[Log, Event]`; consumers are `async def _consume_{logs,events}(self) -> None`.

**Data Shape:** one `asyncio.Queue[Union[Log, Event, Exception, None]]`; `None` = per-stream sentinel; `Exception` instances = deferred failures; `_sentinels_received` counts against `len(self._tasks)` (=2); `_flow_completed` flips on the first terminal event.

### Decisive source
```python
# __aenter__ — both lower streams are forced to survive clean closes:
self._logs_subscriber = get_logs_subscriber(
    filter=self._log_filter, reconnection_attempts=..., reconnect_on_clean_close=True)
self._events_subscriber = get_events_subscriber(
    filter=self._event_filter, reconnection_attempts=..., reconnect_on_clean_close=True)
self._tasks = [asyncio.create_task(self._consume_logs()),
               asyncio.create_task(self._consume_events())]

# __anext__ — sentinel counting + straggler drain:
while self._sentinels_received < len(self._tasks):
    if self._flow_completed:
        try:
            item = await asyncio.wait_for(self._queue.get(), timeout=self._straggler_timeout)
        except asyncio.TimeoutError:
            raise StopAsyncIteration
    else:
        item = await self._queue.get()
    if item is None:
        self._sentinels_received += 1
        continue
    if isinstance(item, Exception):
        raise item
    return item

# each consumer, in its finally/else blocks:
except Exception as exc:
    await self._queue.put(exc)                 # failure travels as an item
else:
    if not self._flow_completed:
        await self._queue.put(ConnectionError("Flow run events stream closed unexpectedly"))
finally:
    await self._queue.put(None)                # sentinel
```

**Flow:** enter → build run-scoped filters (log by flow_run_id, events by resource id `prefect.flow-run.{id}`) → start both consumers → iterate the queue. The events consumer breaks its loop on the first terminal event (`_is_terminal_event`: resource id match AND `prefect.state-type` — or `payload.validated_state.type` fallback — parses into TERMINAL_STATES), setting `_flow_completed`; the LOGS consumer keeps running so late logs still arrive, but the iterator now reads with a `straggler_timeout` (default 3 s) and ends when the tail goes quiet. A stream that closes WITHOUT a terminal event enqueues a `ConnectionError` instead of a silent sentinel — premature closure is an error, not success. Either stream's exception is enqueued and re-raised through the single iterator. Exit cancels both tasks (`gather(return_exceptions=True)`) then exits both subscribers.

**Invariant:** (1) Termination requires ALL sentinels — ending on the first dead stream strands the sibling and leaks its websocket. (2) Exceptions must cross the task boundary as DATA (queue items) or they die inside the consumer task; re-raise them at the iterator. (3) A clean close without the expected terminal marker must be converted to an error — otherwise "server dropped us" looks like "run finished". (4) Lower-level subscribers under a composite must be created with `reconnect_on_clean_close=True`, or a routine clean close ends the whole composite early. (5) Terminal detection must be scoped to THIS run's resource id (test pins another run's terminal event does not stop consumption).

**Probe:** direct tests `tests/events/client/test_flow_run_subscriber.py`: `:259-313 test_flow_run_subscriber_straggler_timeout` (terminal event + slow log stream → exactly 1 item, ends after 0.5 s timeout); `:315-322 test_flow_run_subscriber_empty_streams` (both empty → `ConnectionError` "stream closed unexpectedly"); `:421-456 test_flow_run_subscriber_propagates_non_connection_error` (ValueError from events stream surfaces through the iterator); `:458-511 test_flow_run_subscriber_stops_when_events_close_and_logs_stay_open` (clean close without terminal → ConnectionError, hanging log stream not stranded); `:552-585 test_flow_run_subscriber_only_terminal_events_stop_consumption` and `:587-630 ..._terminal_event_for_different_flow_run`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^FlowRunSubscriber$", "limit": 3}'
```
(expected rank-1: `FlowRunSubscriber Class src/prefect/events/subscribers.py 26-210`; graph was NOT connected in the mining session that authored this capsule — verify live before relying on line numbers.)

## Verdict
Adopt the queue-fan-in shape for any multi-source single-iterator merge: background consumers, None-sentinels counted against task count, exceptions-as-items, unexpected-close→error conversion, and a bounded straggler drain after the completion marker. Adapt the terminal-event predicate and timeout to your domain; omit Prefect's specific LogFilter/EventFilter wiring.
