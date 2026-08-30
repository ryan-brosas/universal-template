<!-- capsule-v2 -->
# WebSocket dual state machine — client_state vs application_state and the OSError→1006 conversion

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** What message sequences are legal on a Starlette WebSocket, and how do send failures become clean disconnects?

## WebSocket.receive — client-side half
**Path/Symbol:** `starlette/websockets.py:WebSocket.receive` (:35-57).
**Data Shape:** `client_state ∈ {CONNECTING, CONNECTED, DISCONNECTED}`.
### Decisive source
```python
if self.client_state == WebSocketState.CONNECTING:
    message = await self._receive()
    if message_type != "websocket.connect": raise RuntimeError(...)
    self.client_state = WebSocketState.CONNECTED
elif CONNECTED:
    ... # only websocket.receive / websocket.disconnect legal
    if disconnect: client_state = DISCONNECTED
else:
    raise RuntimeError('Cannot call "receive" once a disconnect message has been received.')
```
**Flow:** first receive MUST be the connect message; after disconnect observed, further receives raise instead of blocking. `accept()` (:100-110) hides this: it receives-connect-if-needed then sends accept.

## WebSocket.send — application-side half + HTTP-response escape hatch
**Path/Symbol:** `starlette/websockets.py:WebSocket.send` (:59-98).
**Data Shape:** `application_state ∈ {CONNECTING, CONNECTED, DISCONNECTED, RESPONSE}`; from CONNECTING the legal set is `{accept, close, websocket.http.response.start}` — the third enters RESPONSE state where ONLY body messages flow until complete.
### Decisive source
```python
elif self.application_state == WebSocketState.CONNECTED:
    ...
    try:
        await self._send(message)
    except OSError:
        self.application_state = WebSocketState.DISCONNECTED
        raise WebSocketDisconnect(code=1006)     # transport error → protocol-level disconnect
```
**Flow:** close-from-CONNECTING (rejection) and close-from-CONNECTED both land in DISCONNECTED which is terminal for BOTH halves. The RESPONSE branch ends (`more_body` false) by setting DISCONNECTED — a WS handshake answered with HTTP is over.
**Invariant:** the two enums are independent: you can be client-CONNECTED while app-DISCONNECTED (server rejected). RuntimeError text names the exact expected set — tests assert on them, keep wording stable if porting the test suite too.
**Probe:** `tests/test_websockets.py::test_application_close` (:283), `::test_client_disconnect_on_send` (:263), `::test_send_response_duplicate_start` (:409).

## receive_* helpers + iterators
**Path/Symbol:** `starlette/websockets.py:receive_text/bytes/json` (:116-142), `iter_text/bytes/json` (:144-163).
**Data Shape:** helpers assert `application_state == CONNECTED` FIRST ("Need to call accept first"), then convert `_raise_on_disconnect(message)` into `WebSocketDisconnect(code, reason)` exceptions; iter_* wrap that into infinite generators terminated BY the exception (try/except/pass).
**Probe:** `::test_websocket_iter_text` (:169).

## send_denial_response + WebSocketClose
**Path/Symbol:** `starlette/websockets.py:send_denial_response` (:183-187), `WebSocketClose.__call__` (:190-196).
**Flow:** denial requires server extension `websocket.http.response`; router's not_found path sends raw `websocket.close` via the minimal WebSocketClose ASGI app (no WebSocket object needed at routing level).
**Probe:** `::test_send_denial_response` (:310), `::test_send_response_unsupported` (:388).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "WebSocketState", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "send_denial_response", limit: 5 });
```

## Verdict
Adopt both FSMs verbatim — they encode the ASGI WS spec's legality table plus two defensive extras (OSError→1006, terminal-disconnect raise). Adapt the RESPONSE extension branch if your server lacks websocket.http.response. Omit nothing else.
