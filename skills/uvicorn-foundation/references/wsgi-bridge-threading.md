<!-- capsule-v2 -->
# WSGI bridge threading — how does a synchronous WSGI app stream into ASGI without blocking the loop?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What runs on the executor vs the event loop, and why is `call_soon_threadsafe` on every handoff?

## Body fully buffered; wsgi() on ThreadPoolExecutor; sender task drains a deque
**Path/Symbol:** `uvicorn/middleware/wsgi.py` — environ build :27–79, responder orchestration :110–131, thread→loop wakeups :175/:185/:193, a2wsgi preference :196–199.
**Signature:** `async def __call__(self, receive, send) -> None`; `def start_response(self, status, response_headers, exc_info=None) -> None`.
**Data Shape:** `send_queue: deque[ASGISendEvent|None]` + `send_event: asyncio.Event`; sentinel `None` terminates the sender; default pool `max_workers=10`.

### Decisive source
```python
# :124-135 — buffer whole request body first (WSGI reads synchronously)
if more_body:
    body.seek(0, io.SEEK_END)
    while more_body:
        body_message = await receive()
        body.write(body_message.get("body", b""))
        more_body = body_message.get("more_body", False)
    body.seek(0)
environ = build_environ(self.scope, message, body)
wsgi = self.loop.run_in_executor(self.executor, self.wsgi, environ, self.start_response)
sender = self.loop.create_task(self.sender(send))
await asyncio.wait_for(wsgi, None)
```
```python
# :170-193 — WSGI thread pushes chunks; loop wakes via call_soon_threadsafe
for chunk in self.app(environ, start_response):
    self.send_queue.append(response_body); self.loop.call_soon_threadsafe(self.send_event.set)
...
self.send_queue.append(None); self.loop.call_soon_threadsafe(self.send_event.set)
```

**Flow:** drain ALL request-body events into BytesIO (WSGI expects a sync stream) → build PEP-3333 environ (`build_environ`: latin1 path handling, SCRIPT_NAME prefix strip :33–35, duplicate headers comma-joined :75–77, content-length/type hoisted out of HTTP_*) → run the WSGI callable in a ThreadPoolExecutor while a sibling ASGI task drains `send_queue` → each yielded chunk is queued from the worker thread with `call_soon_threadsafe(send_event.set)` waking the loop → trailing None stops the sender → exc_info captured by start_response re-raises AFTER the pipeline unwinds (:130–131). If a2wsgi is importable it replaces this whole module (deprecation shim).
**Invariant:** Every cross-thread queue append MUST pair with a threadsafe wakeup or the sender stalls until the next event. Response ordering is guaranteed because the single worker thread appends sequentially. `wsgi.errors` maps to sys.stdout here (documented quirk).
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'call_soon_threadsafe' uvicorn/uvicorn/middleware/wsgi.py"` → 3; `bash -c "grep -c 'from a2wsgi import WSGIMiddleware' uvicorn/uvicorn/middleware/wsgi.py"` → 1; behavioral pin `tests/middleware/test_wsgi.py:test_build_environ_encoding` :114.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"WSGI environ executor thread pool start_response","limit":5,"detail":"ids"}` → rank#1/2 `start_response`, `build_environ` line-exact; adversarial same query on `ext-analytics` returns unrelated Elixir pools (total:4, wrong-plane).
**Verdict:** Adapt freely — uvicorn itself recommends a2wsgi for new ports. Adopt only the cross-thread queue+wakeup pattern and environ header-join rules if rolling your own.

