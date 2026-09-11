<!-- capsule-v2 -->

# Logs subscriber live-only window — How should a reconnecting consumer of a LOSSY-TOLERANT stream differ from an at-least-once one?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect` (graph not connected this pass — direct source/test reads; see work record). **Question:** When a stream's contract tolerates gaps (logs), what may a reconnecting subscriber skip that an at-least-once subscriber (events) must not?

## A fresh now-minus-1-minute window per reconnect, no rolling cursor, and a retry budget that resets on every successful yield

**Path/Symbol:** `src/prefect/logging/clients.py:PrefectLogsSubscriber (140-345)` — docstring contract (144-146), `_reconnect` window block (268-279), `__anext__` budget/dedup/close policy (293-345). Contrast anchor: `src/prefect/events/clients.py:PrefectEventSubscriber` (see `subscriber-replay-backfill-window`).

**Signature:** `async def __anext__(self) -> Log`; `_reconnect(self) -> None`.

**Data Shape:** filter window recomputed on EVERY (re)connect as `after_=now("UTC") - 1min`, `before_=now + 365d`; no persistent cursor attribute exists at all. Dedup state is the same bounded TTL id cache as the events subscriber: `SEEN_LOGS_SIZE = 500_000`, `SEEN_LOGS_TTL = 120` (:71-72), `TTLCache` at :196.

### Decisive source
```python
# class docstring — the contract that justifies everything below:
#   "The logs stream is live-only, so logs emitted while disconnected
#    may be omitted."

# _reconnect, after auth handshake succeeds — a FRESH window each time:
current_time = now("UTC")
self._filter.timestamp = LogFilterTimestamp(
    after_=current_time - timedelta(minutes=1),
    before_=current_time + timedelta(days=365),
)

# __anext__ — the retry budget is PER-YIELD, not per-connection:
attempts = 0
while attempts <= self._reconnection_attempts:
    ...
    except _RETRYABLE_EXCEPTIONS as exc:
        if isinstance(exc, ConnectionClosedOK):
            if not self._reconnect_on_clean_close:
                raise StopAsyncIteration
        attempts += 1
        ...
        if attempts > self._reconnection_attempts:
            raise          # re-raises the LAST exception, not StopAsyncIteration
        if attempts > 2:
            await asyncio.sleep(1)
```

**Flow:** connect → auth → send fresh timestamp window → iterate. On any retryable disconnect, reconnect with a NEW now-anchored window (the server replays only the last minute, so anything older is accepted as lost). A successful yield returns to the caller and the NEXT `__anext__` starts with `attempts = 0` again — a healthy stream therefore never exhausts its budget; only a stall of N consecutive failed reconnects fails, and it fails with the underlying transport exception re-raised. The trailing `raise StopAsyncIteration` at :345 is unreachable defensive code (the loop can only exit via the inner `raise`). Duplicates from the 1-minute overlap are dropped by the check-before-yield TTL cache (:316-318).

**Invariant:** (1) Lossy tolerance must be EXPLICIT in the contract (docstring here) — silently dropping a gap in a stream the caller believes is complete is the failure this contrast prevents. (2) Per-yield budget reset means "N retries" actually means "N consecutive failures while stalled" — porting it as a per-connection budget changes liveness semantics. (3) Exhaustion re-raises the transport error (test pins `ConnectionClosedError`), so callers can distinguish "server said goodbye" (StopAsyncIteration on clean close) from "gave up" (exception). (4) The dedup cache is still required even without a cursor, because the overlap window still double-delivers.

**Probe:** direct tests `tests/logging/test_logs_subscriber.py`: `:442-458 test_subscriber_gives_up_after_so_many_attempts` (raises `ConnectionClosedError`, `connections == 1 + 4`); `:415-438 test_subscriber_reconnects_on_hard_disconnects` (both logs delivered across a hard disconnect, `connections == 2`); `:470-489 test_subscriber_skips_duplicate_logs` (duplicate id yielded once); `:556-569 test_subscriber_stops_on_clean_disconnect_by_default` (`StopAsyncIteration`, reconnect never awaited); `:572-605 test_subscriber_reconnects_on_clean_disconnect_when_configured` (3 clean closes survived until a log arrives).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^PrefectLogsSubscriber$", "limit": 3}'
```
(expected rank-1: `PrefectLogsSubscriber Class src/prefect/logging/clients.py 140-345`; graph was NOT connected in the mining session that authored this capsule — verify live before relying on line numbers.)

## Verdict
Adopt the split explicitly: for lossy-tolerant streams use a fresh now-anchored replay window per reconnect + per-yield retry budget + re-raise-on-exhaustion; for at-least-once streams keep the delivery-driven cursor (see `subscriber-replay-backfill-window`). Adapt the 1-minute overlap to your redelivery tolerance; omit Prefect's LogFilter message schema and Prometheus counters.
