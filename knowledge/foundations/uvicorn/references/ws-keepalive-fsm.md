<!-- capsule-v2 -->
# WS keepalive ping/pong FSM — how do random payloads, RTT chaining, and the no-timeout branch interact?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What keeps the ping loop alive in BOTH configurations (timeout set vs None), and how are stale pongs rejected?

## schedule→send→pong-cancels-and-rechains; delay = interval − last_rtt
**Path/Symbol:** `uvicorn/protocols/websockets/websockets_sansio_impl.py` — `start_keepalive` :329–332, `schedule_ping` :342–345, `send_keepalive_ping` :347–360, `handle_pong` :315–327, `keepalive_timeout` :362–374; byte-identical FSM in `wsproto_impl.py:300–356`.
**Signature:** `def schedule_ping(self) -> None` / `def send_keepalive_ping(self) -> None` / `def handle_pong(self, event) -> None`.
**Data Shape:** `ping_interval=20.0, ping_timeout=20.0` defaults; `pending_ping_payload: bytes|None`, `ping_sent_at/last_ping_rtt: float`.

### Decisive source
```python
# :353-360 — random 4-byte tag identifies THIS ping
self.pending_ping_payload = struct.pack("!I", random.getrandbits(32))
self.ping_sent_at = self.loop.time()
self.conn.send_ping(self.pending_ping_payload)
...
if self.ping_timeout is not None:
    self.pong_timer = self.loop.call_later(self.ping_timeout, self.keepalive_timeout)
else:
    self.schedule_ping()          # no deadline ⇒ chain the next ping NOW
```
```python
# :315-327 — pong must MATCH the in-flight payload; then cancel + RECHAIN
if self.pending_ping_payload is None or bytes(event.data) != self.pending_ping_payload:
    return                        # unsolicited or stale
self.last_ping_rtt = self.loop.time() - self.ping_sent_at
...
if self.pong_timer is not None:
    self.pong_timer.cancel(); self.pong_timer = None
    self.schedule_ping()          # THE loop-carrier when timeout is set
```

**Flow:** accept → `start_keepalive()` arms the first ping after `ping_interval` → each send stamps a random 32-bit payload + timestamp and EITHER sets the pong deadline (timeout mode) or schedules the next ping directly (interval-only mode) → a matching pong records RTT, cancels the deadline, and re-chains via `schedule_ping()` whose delay is `max(0, interval − last_rtt)` so slow links don't stack pings → unmatched/unsolicited pongs are silently ignored; a missed deadline fails the connection with code 1011 "keepalive ping timeout".
**Invariant:** Exactly one of {pong_timer, immediate re-schedule} may carry the loop per cycle — double-scheduling is the classic port bug (comment at :320–326 warns verbatim). Payload equality check makes delayed replies from a PREVIOUS ping harmless. `stop_keepalive()` clears all three state slots.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'struct.pack(\"!I\", random.getrandbits(32))' uvicorn/uvicorn/protocols/websockets/websockets_sansio_impl.py"` → 1; `bash -c "grep -c 'delay = max(0.0, self.ping_interval - self.last_ping_rtt)' uvicorn/uvicorn/protocols/websockets/websockets_sansio_impl.py"` → 1. Behavioral pins: `tests/protocols/test_websocket.py:test_server_keepalive_ping_pong` :1376 + `test_server_keepalive_ping_timeout` :1415 (parametrized over ws backends).
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"keepalive ping pong stale payload schedule","limit":5,"detail":"ids"}` → ranks the direct test plus both impls' `schedule_ping` line-exact.
**Verdict:** Adopt the two-mode loop-carrier rule and payload-tagged pong matching verbatim. Adapt intervals. Omit websockets-legacy impl (library-managed keepalive there).

