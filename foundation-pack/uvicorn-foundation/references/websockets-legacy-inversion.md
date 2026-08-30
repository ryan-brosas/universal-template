<!-- capsule-v2 -->
# websockets-legacy inversion — why does the ASGI app start BEFORE the handshake, and how does accept/close map onto process_request?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae` (deprecated impl, UvicornDeprecationWarning at :79); Codebase Memory `ext-uvicorn`. **Question:** How is the library's handler-driven model inverted into ASGI's message-driven one?

## process_request starts run_asgi and BLOCKS on handshake_started_event
**Path/Symbol:** `uvicorn/protocols/websockets/websockets_impl.py` — fake Server stub :84–95, inversion hook `process_request` :197–243 (start task :236, await event :240), subprotocol override :218–227, shutdown :152–159, disconnect synthesis in asgi_receive :330–352.
**Signature:** `async def process_request(self, path: str, request_headers: Headers) -> HTTPResponse | None` (websockets library hook).
**Data Shape:** three asyncio Events: `handshake_started_event` (app spoke first), `handshake_completed_event` (101 on wire / connection lost), `closed_event`; `initial_response: HTTPResponse | None` carries pre-handshake HTTP replies.

### Decisive source
```python
# :235-241 — app-first inversion: start ASGI, then FREEZE the handshake
task = self.loop.create_task(self.run_asgi())
task.add_done_callback(self.on_task_complete)
self.tasks.add(task)
await self.handshake_started_event.wait()
return self.initial_response        # None ⇒ proceed to WS handshake; else HTTP reply
```
```python
# :284-295 — accept arm records the app's subprotocol choice for later override
self.accepted_subprotocol = cast(Subprotocol | None, message.get("subprotocol"))
...
self.handshake_started_event.set()
```

**Flow:** library receives request → calls process_request → uvicorn builds the scope, launches run_asgi, and AWAITS until the app sends websocket.{accept|close|http.response.start} → accept sets initial_response=None + started-event so the library completes the 101 itself (with `process_subprotocol()` overridden to return the APP's choice instead of negotiating) → close-before-accept becomes HTTP 403 via initial_response → http.response.start becomes a full custom HTTP reply. Data plane: asgi_receive waits handshake_completed then recv()s, synthesizing 1005/1006/1012 disconnect codes (ws_server.closing flag set by shutdown()).
**Invariant:** The app can NEVER miss a connect: even a crash-before-handshake path sets handshake_started_event inside send_500_response (:252). Every asgi_receive branch returns a well-formed event — no exceptions across the library boundary. Deprecation warning fires at import time of this module.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'process_subprotocol' uvicorn/uvicorn/protocols/websockets/websockets_impl.py"` → 2; `bash -c "grep -c 'return self.accepted_subprotocol' uvicorn/uvicorn/protocols/websockets/websockets_impl.py"` → 1. Behavioral pins: `test_subprotocols` :667, `test_server_reject_connection_with_response` :855, `test_shutdown_waits_for_app_task_to_complete` :1193.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"process_request handshake started event accept subprotocol","limit":5,"detail":"ids"}` → resolves the legacy impl methods line-exact.
**Verdict:** Adopt ONLY if porting onto an invasive WS library that owns its handshake; otherwise prefer the sans-io shape. Adapt event names. Omit entirely when you control the socket (see sansio capsules).

