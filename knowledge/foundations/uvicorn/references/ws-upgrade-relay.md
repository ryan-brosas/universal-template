<!-- capsule-v2 -->
# WebSocket upgrade relay — how does an HTTP connection hand itself to a WebSocket protocol mid-flight?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What bytes does the HTTP protocol replay to the WS protocol, and in what order are transport/protocol swapped?

## Rebuild the raw request, feed it as data, THEN set_protocol
**Path/Symbol:** httptools form: `handle_websocket_upgrade` :316–333 + `_should_upgrade` :248–252 + parser-callback gate in `on_headers_complete` :236; h11 twin `handle_websocket_upgrade(event)` :289–306.
**Signature:** `def handle_websocket_upgrade(self) -> None` (httptools: state already on self; h11: takes the parsed `h11.Request`).
**Data Shape:** upgrade detection = `connection` header contains token `upgrade` AND `upgrade: websocket` (:221–235); requires a WS class resolved (`ws_protocol_class is not None`).

### Decisive source
```python
# httptools_impl.py :316-333
self.connections.discard(self)                    # leave the HTTP registry...
method = self.scope["method"].encode()
output = [method, b" ", self.url, b" HTTP/1.1\r\n"]
for name, value in self.scope["headers"]:
    output += [name, b": ", value, b"\r\n"]
output.append(b"\r\n")
protocol = self.ws_protocol_class(config=self.config, server_state=self.server_state, app_state=self.app_state)
protocol.connection_made(self.transport)          # 1) WS claims the transport
protocol.data_received(b"".join(output))          # 2) replay request as bytes
self.transport.set_protocol(protocol)             # 3) asyncio now routes events there
```

**Flow:** parser signals an upgrade attempt (`HttpParserUpgrade` exception or `should_upgrade()` at headers-complete) → verify `upgrade==websocket` AND a ws backend exists (else warn: unsupported/none-installed) → drop self from shared connections set → SYNTHESIZE the original request line + headers from retained parse state → construct the configured WS protocol → call its `connection_made(transport)` manually → push the synthesized bytes through its `data_received` so its handshake parser sees a fresh stream → only then hand the transport to asyncio via `set_protocol`.
**Invariant:** The replayed byte-stream must be byte-faithful for the handshake (Sec-WebSocket-* headers included verbatim); the WS protocol's own bookkeeping (connections.add in ITS connection_made) makes the handoff atomic from ServerState's perspective. Unsupported upgrades fall through to normal HTTP handling with a warning, never a hard close.
**Probe:** from the uvicorn checkout root: behavioral pins `tests/protocols/test_websocket.py:test_accept_connection` :119 and `test_header_upgrade_is_websocket_depend_not_installed` :1174 (warn-not-close path). Structural: every impl carries the same 4-step tail — `grep -c 'protocol.data_received' uvicorn/uvicorn/protocols/http/httptools_impl.py` → 1.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"websocket upgrade handle set_protocol","limit":5,"detail":"ids"}` → resolves both http-impl `handle_websocket_upgrade` methods line-exact.
**Verdict:** Adopt the manual claim→replay→swap order exactly — reordering breaks asyncio's protocol routing. Adapt header reconstruction to your parser's retained state. Omit per-backend warning texts.

