<!-- capsule-v2 -->
# WS close handshake and lost-transport unblock — who closes first, what code does the app see, and why must send() never hang on a dead socket?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What is the close choreography (app-initiated vs peer-initiated), which disconnect codes are synthesized, and what revives a paused writer when the transport dies?

## close_sent latch + 10s close_timer + writable.set() in connection_lost
**Path/Symbol:** `websockets_sansio_impl.py` — disconnect codes :143, post-close discard rule :293–297, app-initiated close :495–511 (send arm) with timer :508–510, peer-close :376–391, transport-lost unblock :153–156; shutdown path :128–141.
**Signature:** `async def send(self, message)` / `def connection_lost(self, exc)` / `def shutdown(self) -> None`.
**Data Shape:** `close_timeout=10.0` hard ceiling after sending close; synthesized codes 1005 (post-handshake loss), 1006 (pre-handshake/abnormal), 1012 (server shutdown / Service Restart).

### Decisive source
```python
# :143 — code depends on handshake state at loss time
code = 1005 if self.handshake_complete else 1006
self.queue.put_nowait({"type": "websocket.disconnect", "code": code})
...
# :153-156 — asyncio NEVER calls resume_writing() on a lost paused transport
# Unblock any send() awaiting writable: ... the buffer will never drain now.
self.writable.set()
```
```python
# :495-511 — app sends close: echo code to app, frame it, arm the ceiling
self.conn.send_close(code, reason)
output = self.conn.data_to_send(); self.transport.write(b"".join(output))
self.close_sent = True
if self.read_paused:
    self.read_paused = False; self.transport.resume_reading()   # keep reading for the REPLY
self.close_timer = self.loop.call_later(self.close_timeout, self.transport.close)
```

**Flow:** APP-initiated: queue `{disconnect, code}` to the app immediately (it's done), send the close frame, RESUME reads so the peer's echoed close can arrive, arm the 10s force-close. PEER-initiated (`handle_close`): if we had sent one → handshake complete → cancel timer + close transport; else queue the peer's code/reason and reply. Server shutdown mid-connection synthesizes 1012 into the app queue before framing it. After close-sent, inbound data messages are DISCARDED (not queued) so the app's reads stay alive waiting for the close reply rather than erroring early.
**Invariant:** `await self.writable.wait()` at the top of send() can NEVER deadlock because connection_lost sets the event unconditionally (comment documents asyncio's resume_writing-on-lost-transport gap). Every teardown path funnels through exactly ONE transport.close() owner (timer callback or event handler).
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'code = 1005 if self.handshake_complete else 1006' uvicorn/uvicorn/protocols/websockets/websockets_sansio_impl.py"` → 1; `bash -c "grep -c 'discard the message rather than queueing' uvicorn/uvicorn/protocols/websockets/websockets_sansio_impl.py"` → 1. Behavioral pins: `test_client_close` :504, `test_shutdown_waits_for_app_task_to_complete` :1193, `test_frame_after_close_handshake_is_ignored` :1216.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"close handshake timer disconnect code writable","limit":5,"detail":"ids"}` → resolves sansio impl region line-exact.
**Verdict:** Adopt the code-synthesis table, read-resume-after-close-send, and the lost-transport unblock verbatim — all three prevent real hangs/races. Adapt timers. Omit legacy websockets impl differences.

