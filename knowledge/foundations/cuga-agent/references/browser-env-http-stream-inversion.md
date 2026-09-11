<!-- capsule-v2 -->
# HTTP stream transport inversion — how does one long-lived SSE pull connection replace a push WebSocket without rewriting WS-shaped callers?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-cuga-agent`. **Question:** How do you swap a push transport for a client-pulled transport while keeping every caller's `send_request(...) -> dict` contract intact?

## ChromeExtensionCommunicatorProtocol + ChromeExtensionCommunicatorHTTP
**Path/Symbol:** `src/cuga/backend/browser_env/browser/gym_obs/http_stream_comm.py:ChromeExtensionCommunicatorProtocol` (6–33), `:ChromeExtensionCommunicatorHTTP` (36–160); server side `src/cuga/backend/server/main.py:extension_command_stream` / `:extension_command_result` (2357–2390).
**Signature:** `async def send_request(self, data: dict, timeout: Optional[float] = None) -> dict`; state = `_queue: asyncio.Queue[dict]` + `_pending: Dict[str, asyncio.Future]`, `request_timeout = 30`.
**Data Shape:** command dicts gain `"request_id"` (uuid4 hex); results come back as whole JSON bodies posted by the extension carrying that id; extraction responses are `{type, data}` envelopes unwrapped to `.get("data", default)` per method.

### Decisive source
```python
# http_stream_comm.py:50-59 — send_request ENQUEUES for pull delivery, awaits an id-keyed future
req_id = uuid.uuid4().hex
data["request_id"] = req_id
fut = asyncio.get_running_loop().create_future()
self._pending[req_id] = fut
await self._queue.put(data)
try:
    return await asyncio.wait_for(fut, timeout or self.request_timeout)
finally:
    self._pending.pop(req_id, None)
```
```python
# main.py:2373-2390 — the extension PULLS commands over SSE and POSTs results back
@app.get("/extension/command_stream")
async def extension_command_stream():
    comm = get_communicator()
    async def event_gen():
        while True:
            cmd = await comm.get_next_command()
            yield f"data: {json.dumps(cmd)}\n\n"
    return StreamingResponse(event_gen(), media_type="text/event-stream")

@app.post("/extension/command_result")
async def extension_command_result(request: Request):
    comm = get_communicator()
    data = await request.json()
    req_id = data.get("request_id")
    comm.resolve_request(req_id, data)
    return JSONResponse({"status": "ok"})
```

**Flow:** `send_request` → register future → enqueue → extension's forever-SSE `GET /extension/command_stream` dequeues (`get_next_command`) and frames it as `data: {json}\n\n` → extension executes in the browser → `POST /extension/command_result {request_id, ...}` → `resolve_request` sets the future (only if not done) → sender wakes.
**Invariant:** the flow INVERSION is invisible to callers because the class implements the full `ChromeExtensionCommunicatorProtocol` vocabulary (runtime_checkable Protocol: async CM, send_request, send_extraction_request, get_next_command, resolve_request, is_connected, wait_for_connection, ping, all extract_* methods) and shims the connection lifecycle (`__aenter__`/`__aexit__` no-op, `is_connected()→True`, `wait_for_connection→pass`) that only made sense for WS.
**Probe:** deterministic probe executed against the repo venv: create `ChromeExtensionCommunicatorHTTP`, start `send_request({"type":"ping"}, timeout=5)` as a task, assert the command surfaces on `get_next_command()` with matching `request_id`, then `resolve_request(rid, {"type":"pong"})` completes the sender with the full body.
**Executed:** `cd $REFERENCE_ROOT/cuga-agent && PYTHONPATH=src .venv/bin/python -c "import asyncio; from cuga.backend.browser_env.browser.gym_obs.http_stream_comm import ChromeExtensionCommunicatorHTTP as C; c = C(); exec('''\nasync def m():\n    t = asyncio.create_task(c.send_request({'type':'ping'}, timeout=5))\n    cmd = await c.get_next_command()\n    assert cmd['type']=='ping' and cmd['request_id']\n    body = {'type':'pong','echo':1}\n    c.resolve_request(cmd['request_id'], body)\n    assert (await t) is body\n    print('OK')\n'''); asyncio.run(m())"` → `OK`. (Note: the sender resolves to EXACTLY the posted body object — `resolve_request` does not merge or re-key it; the first run of this probe failed only because it expected a synthesized dict.)
**Selection alias:** `extract_chrome_extension.py:39 ChromeExtensionCommunicator = ChromeExtensionCommunicatorHTTP` — module-level alias picks the HTTP transport (the stale comment above it still says "WebSocket server-based"); lifespan selects the ENV by `settings.advanced_features.use_extension`, so porters must not wire the WS class here.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-cuga-agent", query: "ChromeExtensionCommunicatorHTTP resolve_request get_next_command command_stream command_result", limit: 10 });
```

## Verdict
Adopt the queue+future inversion with finally-pop cleanup and the Protocol shim set that keeps WS-written callers unchanged. Adapt framing (`data: {json}\n\n` SSE vs your transport) and the always-connected stubs if you keep real liveness signals. Omit nothing structural — dropping any single protocol method breaks runtime_checkable duck-typing consumers. Caveat: no upstream direct test covers this file; synthetic probe above stands in.
