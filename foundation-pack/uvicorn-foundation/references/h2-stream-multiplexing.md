<!-- capsule-v2 -->
# H2 stream multiplexing — how do per-stream cycles, GOAWAY, and cross-stream read gating extend the HTTP/1 model?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae` (commit cf775d6 "Add experimental HTTP/2 support via zttp"); Codebase Memory `ext-uvicorn`. **Question:** How does one asyncio connection host many concurrent ASGI cycles, and what does graceful shutdown mean when streams share a connection?

## cycles dict keyed by stream_id; refuse-new-after-GOAWAY; idle-frames re-arm keep-alive
**Path/Symbol:** `uvicorn/protocols/http/zttp_h2_impl.py` — FORBIDDEN_HEADERS :33, cycles dict :87, event arms :176–193 (`RstStream` :183, `GoAway` :185), request handler :195–255, `resume_reading_if_idle` :266–272, `on_stream_closed` :282–300, shutdown :310–320, header strip :444–458.
**Signature:** `def on_response_complete(self, stream_id: int) -> None`; `async def send(self, message)` per-cycle (stream-scoped).
**Data Shape:** `self.cycles: dict[int, RequestResponseCycle]`; `shutdown_requested:bool`; per-class `alpn_protocols = ["h2"]`.

### Decisive source
```python
# :183-192 + :266-272 — reset kills one cycle; GOAWAY flips the latch
elif isinstance(event, zttp.RstStream):
    self.handle_rst_stream(event)
elif isinstance(event, zttp.GoAway):
    self.shutdown_requested = True
    if not self.cycles:
        self._close_connection()
...
def resume_reading_if_idle(self) -> None:
    for cycle in self.cycles.values():
        if len(cycle.body) > HIGH_WATER_LIMIT:
            return                    # ONE slow stream holds the whole transport
    self.flow.resume_reading()
```
```python
# :444-455 — RFC 9113 §8.2.2: strip connection-specific headers on the way OUT
if name in FORBIDDEN_HEADERS: continue
if name == b"te" and value.lower().strip() != b"trailers": continue
```

**Flow:** each Request event spawns its own RequestResponseCycle + ASGI task stored under `stream_id`; Data/EndOfMessage route to the right cycle; RstStream pops + marks disconnected (app sees http.disconnect) while siblings live; app crash mid-response calls `stream.reset()` (abort_stream) instead of closing the transport. Graceful shutdown sets `shutdown_requested`: new streams get service_unavailable 503, and the transport closes when the LAST cycle completes. Keep-alive timer re-arms after frame batches that carry no stream event (:157–163 comment) since SETTINGS/PING/WINDOW_UPDATE cancel-but-never-rearm it in `data_received`.
**Invariant:** Read-side backpressure is CONNECTION-level: any single stream over HIGH_WATER_LIMIT pauses the whole transport (documented trade-off at :267–270). Response header pass silently DROPS `connection`, `keep-alive`, `transfer-encoding`, `upgrade`, non-trailer `te` — an HTTP/1-tuned middleware emitting them must not break h2.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'FORBIDDEN_HEADERS = frozenset' uvicorn/uvicorn/protocols/http/zttp_h2_impl.py"` → 1; `bash -c "grep -c 'zttp.GoAway' uvicorn/uvicorn/protocols/http/zttp_h2_impl.py"` → 1; `bash -c "grep -cF 'or status < 200' uvicorn/uvicorn/protocols/http/zttp_h2_impl.py"` → 1. Behavioral pins: `tests/protocols/test_http2.py:test_goaway_closes_idle_connection` :655, `test_shutdown_refuses_new_streams_and_closes_after_last_response` :618, `test_resume_reading_waits_for_other_buffered_streams` :678, `test_connection_specific_response_headers_are_stripped` :451.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"connection-specific response headers stripped forbidden","limit":5,"detail":"ids"}` → rank#1 the direct test :451-483 line-exact.
**Verdict:** Adopt stream-keyed cycle map + GOAWAY latch + forbidden-header stripping verbatim for any multiplexed protocol. Adapt the read-gating policy (per-window credit is the production-grade upgrade). Omit ztplib internals.

