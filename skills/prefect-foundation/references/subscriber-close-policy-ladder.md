<!-- capsule-v2 -->

# Subscriber close-policy ladder — Should a clean server close end iteration, and how many disconnects in a row do you tolerate?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** How does an event-stream iterator distinguish "server is done with me" from "the network hiccuped", and how does its retry budget survive long uptimes?

## Clean close ends iteration by default; abnormal closes retry; the failure counter resets after EVERY successful reconnect

**Path/Symbol:** `src/prefect/events/clients.py:PrefectEventSubscriber.__anext__ (871-936)`; initial-connect twin `__aenter__ (772-796)`; guarded teardown `__aexit__ (853-866)`. Retrieve anchor: `PrefectEventSubscriber.__anext__ Method 871-936` (file-scoped `__anext__` retrieve).

**Signature:** `__init__(..., reconnection_attempts: int = 10, reconnect_on_clean_close: bool = False)`; `RETRYABLE_EXCEPTIONS = (ConnectionClosed, TimeoutError, OSError)`.

**Data Shape:** two independent counters — `consecutive_failures` (abnormal) and `consecutive_clean_closes` (`ConnectionClosedOK` only); both reset to 0 after each successful `_reconnect`.

### Decisive source
```python
while consecutive_failures <= self._reconnection_attempts:
    try:
        if not self._websocket or consecutive_failures > 0:
            await self._reconnect()
            ...
            consecutive_failures = 0        # reset after EVERY success
        while True:
            message = orjson.loads(await self._websocket.recv())
            ...
            return event
    except RETRYABLE_EXCEPTIONS as exc:
        if isinstance(exc, ConnectionClosedOK):
            if not self._reconnect_on_clean_close:
                raise StopAsyncIteration    # clean close == server said goodbye
            consecutive_clean_closes += 1
        consecutive_failures += 1
        attempts = (consecutive_clean_closes if isinstance(exc, ConnectionClosedOK)
                    else consecutive_failures)
        if attempts > self._reconnection_attempts:
            raise                           # last exception propagates
        if attempts > 2:                    # first two fast: likely just an
            await asyncio.sleep(1)          # LB timeout; then take a beat
raise StopAsyncIteration

# __aexit__:
self._websocket = None
if hasattr(self._connect, "connection"):    # websockets sets .connection only
    await self._connect.__aexit__(...)      # after __aenter__ succeeded
```

**Flow:** `ConnectionClosedOK` means the server closed deliberately — by default the subscriber treats that as end-of-stream (`StopAsyncIteration`) rather than spinning against a shut-down server; opt-in `reconnect_on_clean_close` keeps iterating under its own counter. Everything else in RETRYABLE_EXCEPTIONS counts as abnormal. The decisive subtlety: because each successful reconnect zeroes the counter, the budget limits CONSECUTIVE failures only — a client with repeated brief outages never exhausts it (regression test for issue #18428). The same ladder shape (attempts+1 tries, no sleep for first two, then 1 s) is duplicated for the INITIAL connection in `__aenter__`, which retries only `(ConnectionClosed, TimeoutError)` and lets any other exception (e.g. ValueError from config) propagate on first occurrence.

**Invariant:** (1) Clean-vs-abnormal is a POLICY fork, not just an error log: default clean ⇒ end iteration. (2) Retry budgets are per-streak, not lifetime — reset on every success so uptime is unbounded. (3) Exhausting clean-close attempts re-raises `ConnectionClosedOK` itself (not StopAsyncIteration) when `reconnect_on_clean_close=True`. (4) Teardown guards against cleaning up a connection whose establishment failed.

**Probe:** direct tests `tests/events/client/test_events_subscriber.py`: `:336-349 test_subscriber_stops_on_clean_disconnect_by_default` (StopAsyncIteration, `_reconnect.assert_not_awaited`), `:352-372 ..._reconnects_on_clean_disconnect_when_configured`, `:375-391 test_subscriber_limits_consecutive_clean_disconnects` (raises ConnectionClosedOK at budget), `:394-418 ..._gives_up_after_so_many_attempts` (`recorder.connections == 1 + 4`), `:442-484 / :487-525 / :528-559 / :562-593` initial-connect ladder (retries only ConnectionClosed/TimeoutError; call_count == attempts+1; non-retryable tried once), `:596-644 test_subscriber_resets_retry_counter_after_successful_reconnect` (reconnect_count == 4 > reconnection_attempts=2).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "__anext__", "file_pattern": "src/prefect/events/clients.py", "limit": 3}'
```
(observed rank-1 line-exact: `PrefectEventSubscriber.__anext__ Method src/prefect/events/clients.py 871-936`)

## Verdict
Adopt the clean/abnormal close fork and per-streak reset retry budgets for any long-lived consumer; adapt the exception set and sleep cadence; omit websockets-library-specific teardown guard details beyond "guard cleanup on successful establishment".
