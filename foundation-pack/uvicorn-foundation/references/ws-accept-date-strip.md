<!-- capsule-v2 -->
# SansIO accept-time Date-header strip — why is the handshake response's Date deleted before merging app headers?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What exactly happens to default headers on `websocket.accept`, and which recent fix prevents a duplicate Date?

## websockets library pre-stamps Date; uvicorn deletes it, then merges defaults+app
**Path/Symbol:** `uvicorn/protocols/websockets/websockets_sansio_impl.py:send` accept arm (:427–457) — strip at :452, merge :445–451; subprotocol append :449–450.
**Signature:** inside `async def send(self, message: ASGISendEvent)` first-phase arm (`websocket.accept`).
**Data Shape:** `self.response: websockets.http11.Response` created by `conn.accept(event)` in `handle_connect` :224 (library already inserted its own `Date`); merged as latin-1 STRINGS then re-encoded by the library.

### Decisive source
```python
# :443-455 — delete-then-merge order is the whole fix
headers = [
    (name.decode("latin-1").lower(), value.decode("latin-1"))
    for name, value in (self.default_headers + list(message.get("headers", [])))
]
accepted_subprotocol = message.get("subprotocol")
if accepted_subprotocol:
    headers.append(("Sec-WebSocket-Protocol", accepted_subprotocol))
del self.response.headers["Date"]        # b783dac: avoid duplicate Date (library + defaults)
self.response.headers.update(headers)
```

**Flow:** client Request arrives → `ServerProtocol.accept()` builds the 101 Response object and the websockets library inserts its own Date → ASGI app sends `websocket.accept` with optional extra headers → uvicorn lowercases default_headers (server/date!) plus app headers into one list → DELETES the library's Date from the response object → `update()` overwrites/appends the merged list (date re-added from server defaults if enabled). Only then `send_response(self.response)` serializes.
**Invariant:** Exactly ONE Date header can survive; deleting before update (rather than after) means even an absent date_header still yields the library's single stamp. Header names are lowercased on merge so case variants can't bypass dedup. Subprotocol must be appended AFTER the merge so it isn't clobbered.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'del self.response.headers[\"Date\"]' uvicorn/uvicorn/protocols/websockets/websockets_sansio_impl.py"` → 1. Behavioral pins: `tests/protocols/test_websocket.py:test_default_server_headers` :1240, `test_no_date_header` :1282, `test_multiple_server_header` :1305.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"accept response headers date subprotocol","limit":5,"detail":"ids"}` → resolves the accept arm region line-exact.
**Verdict:** Adopt delete-before-merge for library-authored response objects. Adapt header casing rules. Omit legacy-impl path (it never lets the library pre-stamp).

