<!-- capsule-v2 -->
# h11 PAUSED pipelining twin — how does the h11 backend order pipelined requests WITHOUT an explicit queue?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What replaces httptools' deque when the parser itself buffers, and where is `start_next_cycle` legal?

## Parser-state-driven ordering: PAUSED ⇒ pause reads; DONE/DONE ⇒ replay
**Path/Symbol:** `uvicorn/protocols/http/h11_impl.py:handle_events` (:163–287) — PAUSED arm :191–196; EndOfMessage DONE arm :274–279; replay in `on_response_complete` :332–341.
**Signature:** `while True: event = self.conn.next_event()` with arms NEED_DATA / PAUSED / Request / Data / EndOfMessage.
**Data Shape:** h11 `Connection(our_state, their_state)`; transition to next request only via `conn.start_next_cycle()`.

### Decisive source
```python
# :191-196 — parser says "I have a full buffered second request"
elif event is h11.PAUSED:
    # stop reading; buffered events handled at end of active cycle
    self.flow.pause_reading()
    break
...
# :274-279 — response for request N fully WRITTEN (our_state DONE)
if self.conn.our_state is h11.DONE:
    self.transport.resume_reading()
    self.conn.start_next_cycle()
    continue
```
```python
# :332-341 — after ASGI completion
self.timeout_keep_alive_task = self.loop.call_later(self.timeout_keep_alive, self.timeout_keep_alive_handler)
self.flow.resume_reading()
if self.conn.our_state is h11.DONE and self.conn.their_state is h11.DONE:
    self.conn.start_next_cycle()
    self.handle_events()      # REPLAY buffered request synchronously
```

**Flow:** h11 internally queues the next request's bytes and reports PAUSED once its buffer holds a complete follow-up request; uvicorn answers by pausing transport reads. Ordering emerges from state: after the app finishes AND frames are flushed (`our_state==DONE`), `start_next_cycle()` rotates the FSM and `handle_events()` re-runs so the buffered Request event fires NOW — no explicit deque exists. Keep-alive timer still arms on every completion but is cancelled by arriving bytes.
**Invariant:** `start_next_cycle()` must be called exactly once per completed exchange and only when BOTH sides are DONE (calling early raises LocalProtocolError). Data events arriving while `our_state is DONE` are dropped (`continue` :270) — they belong to the NEXT request which hasn't started yet.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'event is h11.PAUSED' uvicorn/uvicorn/protocols/http/h11_impl.py"` → 1; `bash -c "grep -c 'start_next_cycle' uvicorn/uvicorn/protocols/http/h11_impl.py"` → 2; `bash -c "grep -c 'they_are_waiting_for_100_continue' uvicorn/uvicorn/protocols/http/h11_impl.py"` → 1.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"h11 paused start_next_cycle handle_events","limit":5,"detail":"ids"}` → resolves `H11Protocol.handle_events` region line-exact.
**Verdict:** Adopt as the reference for "parser-with-buffer" backends; contrast with httptools deque shows both valid designs. Adapt arm order carefully — MUST_CLOSE break at :282 prevents close-frame loss. Omit h11 400-response event serialization details.

