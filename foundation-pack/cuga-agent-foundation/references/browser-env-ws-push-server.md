<!-- capsule-v2 -->
# WebSocket push server — how does a server push commands to a browser extension and pair async responses without blocking its receive loop?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** How do you run a WS server whose request/response pairs are matched by id while the connection handler keeps receiving messages?

## ChromeExtensionWebSocketServer lifecycle + message router
**Path/Symbol:** `src/cuga/backend/browser_env/browser/gym_obs/websocket_server.py:ChromeExtensionWebSocketServer` (`start`/`stop` 24–44, `handle_client` 46–73, `handle_message` 75–116, `send_request` 150–182).
**Signature:** `async def send_request(self, data: Dict[str, Any], timeout: Optional[float] = None) -> Dict[str, Any]`; state = `connected_clients: Dict[str, WebSocketServerProtocol]` (uuid4 keys) + `pending_requests: Dict[str, asyncio.Future]`, both instance-level, `request_timeout = 30`.
**Data Shape:** requests are dicts mutated in place with `data["request_id"] = str(uuid4())`; responses arrive as full JSON messages echoing that `request_id`.

### Decisive source
```python
# websocket_server.py:150-163, 173-182 — first-client pick, future map, cleanup ONLY on timeout/error
websocket = next(iter(self.connected_clients.values()))
request_id = str(uuid.uuid4())
data["request_id"] = request_id
future = asyncio.get_running_loop().create_future()
self.pending_requests[request_id] = future
...
except asyncio.TimeoutError:
    if request_id in self.pending_requests:
        del self.pending_requests[request_id]
    raise TimeoutError(f"Request {request_id} timed out")
```
```python
# websocket_server.py:110-114 — success-path pop happens on the RECEIVE side
elif request_id and request_id in self.pending_requests:
    future = self.pending_requests.pop(request_id)
    if not future.cancelled():
        future.set_result(data)
```

**Flow:** `websockets.serve(self.handle_client, ...)` → per-connection uuid registered in `connected_clients` → inbound loop dispatches by `type` (`ping`→pong, `extension_ready`→server_ready, `page_extraction_complete`→handler+ack, `agent_query`→`asyncio.create_task` so the receive loop never pauses) → unmatched messages with a known `request_id` resolve the waiting future → disconnect removes the client in `finally`.
**Invariant:** the receive loop must never await an outbound request's response inline — `handle_message` spawns `handle_agent_query` as a task precisely because sending a sub-request from inside the handler would deadlock against the paused receive loop; and every pending future is popped exactly once (receive-side on success, sender-side only on timeout/error).
**Probe:** no upstream test references this file (grep over `tests/` finds zero) — coverage caveat recorded. Deterministic probe executed against the repo venv: instantiate `ChromeExtensionWebSocketServer()`, pre-load `pending_requests["rid"]=loop.create_future()` and call `await server.handle_message("c", None, {"type":"pong-ish","request_id":"rid","x":1})` → future resolves to the full message dict and `pending_requests` is empty.
**Executed:** `.venv/bin/python -c "import asyncio;from cuga.backend.browser_env.browser.gym_obs.websocket_server import ChromeExtensionWebSocketServer as S;s=S();f=asyncio.get_event_loop().create_future();s.pending_requests['rid']=f;asyncio.get_event_loop().run_until_complete(s.handle_message('c',None,{'type':'resp','request_id':'rid','v':7}));assert f.result()['v']==7 and not s.pending_requests;print('OK')"` with `PYTHONPATH=src` → `OK`.
**Source quirk preserved:** `start()` defines a nested `async def handler(websocket, path)` closure that is DEAD CODE — `websockets.serve` receives `self.handle_client` directly (lines 28–33). Do not "fix" one into the other when porting; pick one signature.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "ChromeExtensionWebSocketServer handle_client handle_message pending_requests lifecycle", limit: 10 });
```

## Verdict
Adopt the id-keyed future map with receive-side pop, the create-task escape for handler-originated sub-requests, and first-connected-client selection. Adapt client registry shape (uuid keys vs list) and ping/keepalive intervals to your host. Omit the dead `handler` closure and the DEBUG double-logging lines. Caveat: no upstream direct test pins this file; the probe above is synthetic.
