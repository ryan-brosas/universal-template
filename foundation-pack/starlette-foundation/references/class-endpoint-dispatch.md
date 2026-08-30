<!-- capsule-v2 -->
# HTTPEndpoint class-based dispatch — method table + HEAD fallback + WS lifecycle hooks

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How does a class endpoint map HTTP verbs to methods, and what is the disconnect-code contract for WebSocketEndpoint?

## HTTPEndpoint.__init__ / dispatch
**Path/Symbol:** `starlette/endpoints.py:HTTPEndpoint` (:17-55).
**Data Shape:** `_allowed_methods` computed ONCE at construction by probing `getattr(self, verb.lower())` over the fixed 7-verb list; instances are ASGI apps via `__await__` → `dispatch()`.
### Decisive source
```python
handler_name = "get" if request.method == "HEAD" and not hasattr(self, "head") else request.method.lower()
if request.method in self._allowed_methods or (request.method == "HEAD" and "GET" in self._allowed_methods):
    handler = getattr(self, handler_name)
else:
    handler = self.method_not_allowed
```
**Flow:** HEAD falls back to GET's handler when no explicit head exists (response body discarded by server, headers kept — content-length stays honest). method_not_allowed mirrors Route.handle's dual mode: raises HTTPException(405, Allow=...) inside an app, returns PlainTextResponse standalone.
**Probe:** `tests/test_endpoints.py::test_http_endpoint_does_not_dispatch_non_verb_method` (:50), `::test_http_endpoint_route_method` (:43).

## WebSocketEndpoint.dispatch — close-code ledger
**Path/Symbol:** `starlette/endpoints.py:WebSocketEndpoint.dispatch` (:70-89) + `decode` (:91-117).
### Decisive source
```python
close_code = status.WS_1000_NORMAL_CLOSURE
try:
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.receive":
            data = await self.decode(websocket, message)
            await self.on_receive(websocket, data)
        elif message["type"] == "websocket.disconnect":
            close_code = int(message.get("code") or WS_1000_NORMAL_CLOSURE)
            break
except Exception as exc:
    close_code = WS_1011_INTERNAL_ERROR
    raise exc                      # handler STILL notified with 1011 in finally
finally:
    await self.on_disconnect(websocket, close_code)
```
**Flow:** three exit paths each pin a code: client-sent disconnect → echo client's code (or 1000); app exception → 1011 AND re-raise; clean loop end impossible without one of those. `decode` enforces `encoding` class attr: wrong channel type or malformed JSON closes with WS_1003_UNSUPPORTED_DATA before raising RuntimeError.
**Invariant:** on_disconnect runs in `finally` even when the exception propagates — cleanup hooks see the REAL close cause via the code argument.
**Probe:** `::test_websocket_endpoint_on_disconnect` (:168), `::test_websocket_endpoint_on_receive_json_binary` (:118), `::test_websocket_endpoint_on_default` (:154).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "dispatch", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "decode", limit: 10 });
```

## Verdict
Adopt the method-table-at-init pattern and the close-code ledger wholesale. Adapt the verb set to your framework's. Omit sync-handler threadpool hops here if your routing layer already does it (this file delegates nothing — endpoints call handlers directly).
