<!-- capsule-v2 -->

# Events websocket resend + checkpointing — How do you deliver events over a flaky socket without losing or re-sending more than necessary?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** What is the buffer/retry/acknowledgment discipline that makes websocket event delivery at-least-once with minimal duplicate resend?

## Buffer-before-send; ping = ack of the prefix; time-based checkpoint reconnects idle dead connections

**Path/Symbol:** `src/prefect/events/clients.py:PrefectEventsClient (275-603)` — `_emit (557-603)`, `_reconnect (422-467)`, `_checkpoint (537-555)`, `_force_checkpoint/_checkpoint_loop (479-535)`, `RETRYABLE_EXCEPTIONS (83-87)`; Cloud auth override `PrefectCloudEventsClient (647-686)`.

**Signature:** `__init__(api_url, reconnection_attempts=10, checkpoint_every=700, checkpoint_interval=30.0)`; `_unconfirmed_events: List[Event]`.

**Data Shape:** retryable set `(ConnectionClosed, TimeoutError, OSError)`; unconfirmed buffer is FIFO; a pong acknowledges everything enqueued BEFORE it.

### Decisive source
```python
async def _emit(self, event):
    self._unconfirmed_events.append(event)
    for i in range(self._reconnection_attempts + 1):
        try:
            if not self._websocket or i > 0:
                await self._reconnect()   # resends unconfirmed first
                assert self._websocket
            await self._websocket.send(event.model_dump_json())
            await self._checkpoint()
            return
        except RETRYABLE_EXCEPTIONS as e:
            if i == self._reconnection_attempts:
                self._log_connection_error(e); raise
            if i > 2:                      # first two attempts fast — likely
                await asyncio.sleep(1)     # just a load-balancer timeout

async def _checkpoint(self):
    unconfirmed_count = len(self._unconfirmed_events)
    if unconfirmed_count < self._checkpoint_every:
        return
    pong = await self._websocket.ping(); await pong
    # once the pong returns ... don't clear the list, just the ones we're sure of
    self._unconfirmed_events = self._unconfirmed_events[unconfirmed_count:]
```
```python
# _reconnect resend tail:
try:
    while events_to_resend:
        await self.emit(events_to_resend.pop(0))
except Exception:
    # restore events never attempted so a later reconnect can retry them;
    # the event whose emit() failed was already re-buffered by emit itself
    self._unconfirmed_events.extend(events_to_resend); raise
```

**Flow:** every emit appends to the buffer BEFORE sending. On ConnectionClosed/Timeout/OSError: reconnect → tear down old socket → connect → ping-pong liveness verify → subprotocol auth handshake (self-hosted JSON {"type":"auth","token"} expecting auth_success; Cloud overrides to no-op and authenticates via bearer HTTP header instead) → resend buffered events → then send the new one. Count-based checkpoint pings every 700 unconfirmed and clears exactly the confirmed PREFIX; an independent 30 s `_checkpoint_loop` force-checkpoints low-throughput buffers and RECONNECTS when unconfirmed events sit on a dead connection, retrying each interval until the server returns.

**Invariant:** (1) At-least-once delivery: duplicates are acceptable, losses are not — the buffer is appended pre-send and only ping-acknowledged prefixes are cleared. (2) Partial-resend failure restores UNATTEMPTED events (the failed one is already re-buffered by its own emit) — restoring by extend preserves order without double-buffering the failed event. (3) First two reconnect attempts sleep nothing (LB blip), later ones wait 1 s. (4) Time-based checkpoint exists so an idle sender doesn't strand events until the next emit.

**Probe:** direct tests `tests/events/client/test_events_client.py:201 test_reconnects_and_resends_after_hard_disconnect` (all five delivered in order across one reconnect), `:238 test_gives_up_after_a_certain_amount_of_tries` (connections == 1+attempts), `:773 test_background_checkpoint_clears_unconfirmed_events`, `:830 test_background_checkpoint_reconnects_after_connection_loss` (double delivery accepted :855-857), `:890 test_failed_resend_does_not_drop_unattempted_events`.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^PrefectEventsClient$", "limit": 3}'
```
(observed rank-1: `PrefectEventsClient Class src/prefect/events/clients.py 275-603`)

## Verdict
Adopt buffer-before-send + pong-as-prefix-ack + dual count/time checkpoints for lossy-intolerant streams; adapt transport (websocket→gRPC stream etc.) and thresholds; omit the Cloud-vs-server auth split beyond "handshake shape differs per endpoint".
