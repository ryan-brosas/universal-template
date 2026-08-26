<!-- capsule-v2 -->
# TestClient transport — in-process ASGI over httpx, portal bridging, lifespan context manager

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How does a sync test client execute async ASGI apps, and how do WS sessions + lifespan ride the same machinery?

## _TestClientTransport.handle_request — scope synthesis + message collection
**Path/Symbol:** `starlette/testclient.py:_TestClientTransport.handle_request` (:225-374).
**Data Shape:** builds full ASGI scope from httpx.Request (host header only if absent; unquoted path; raw_path minus query); runs the app via a BLOCKING PORTAL (`portal.call(self.app, scope, receive, send)`) so the sync httpx transport can await it.
### Decisive source
```python
elif message["type"] == "http.response.body":
    ...
    if request.method != "HEAD":
        raw_kwargs["stream"].write(body)
    if not more_body:
        raw_kwargs["stream"].seek(0); response_complete.set()
...
except BaseException as exc:
    if self.raise_server_exceptions: raise exc      # default: tests FAIL on app errors
...
assert response_started, "TestClient did not receive any response."
```
**Flow:** HEAD requests collect content-length but discard bytes; `raise_server_exceptions=False` converts unstarted apps into synthetic 500s; `http.response.debug` messages surface as response extensions (template/context introspection).
**Probe:** `tests/test_testclient.py::test_error_on_startup` (:167), `::test_debug_info_in_response_extensions` (:233).

## WebSocketTestSession — exception-as-upgrade protocol
**Path/Symbol:** `starlette/testclient.py:WebSocketTestSession` (:102-204), `_Upgrade` (:87-89), `websocket_connect` (:656-677).
**Data Shape:** ws scopes are detected by scheme; the transport RAISES `_Upgrade(session)` out of the normal request path; `websocket_connect` catches it and returns the session. Session body: portal task runs the real app against memory-object streams (infinite capacity); sync side sends/receives through `portal.call`.
### Decisive source
```python
def __enter__(self) -> Self:
    with contextlib.ExitStack() as stack:
        self.portal = portal = stack.enter_context(self.portal_factory())
        fut, cs = portal.start_task(self._run)
        stack.callback(fut.result)              # reap the app task at exit
        stack.callback(portal.call, cs.cancel)
        self.send({"type": "websocket.connect"})
        message = self.receive(); self._raise_on_close(message)   # rejection → WebSocketDisconnect HERE
        ...stack.callback(self.close, 1000)     # implicit clean close on exit
```
**Flow:** `_raise_on_close` also translates `websocket.http.response.*` denial sequences into WebSocketDenialResponse (multiple-inheritance httpx.Response × WebSocketDisconnect). ExitStack ordering guarantees cancel → close → task-reap sequence.
**Probe:** `tests/test_testclient.py::test_websocket_blocking_receive` (:272), `tests/test_websockets.py::test_rejected_connection` (:296).

## Lifespan context manager
**Path/Symbol:** `starlette/testclient.py:TestClient.__enter__` (:679-706), `lifespan/wait_startup/wait_shutdown` (:711-749).
**Flow:** `with TestClient(app):` starts ONE long-lived portal + streams; startup sends `lifespan.startup`, asserts complete/failed, and on failed RE-RAISES the app's exception via `self.task.result()`. `app_state` dict is shared by reference into every request scope's `"state"` — cross-request state persistence in tests.
**Probe:** `::test_use_testclient_as_contextmanager` (:89), `::test_error_on_startup` (:167).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "WebSocketTestSession", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "wait_startup", limit: 5 });
```

## Verdict
Adopt the portal-bridge pattern for any sync-over-async testing need. Adopt the upgrade-exception trick only if you control both ends. Adapt httpx2/httpx import fallback to your dependency policy. Omit ASGI2 support (_WrapASGI2/_is_asgi3) when your floor is spec 3.0.
