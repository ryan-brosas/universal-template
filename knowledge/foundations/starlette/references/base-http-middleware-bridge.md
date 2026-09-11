<!-- capsule-v2 -->
# BaseHTTPMiddleware call_next — memory-stream bridge, disconnect races, exception re-raising

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** Why is writing an http.request/response middleware hard, and what exact machinery keeps the downstream ASGI app decoupled from a dispatch function that wants Request/Response?

## _CachedRequest.wrapped_receive — 3-state body replay FSM
**Path/Symbol:** `starlette/middleware/base.py:_CachedRequest.wrapped_receive` (:34-93).
**Data Shape:** states keyed by flags `_wrapped_rcv_disconnected`, `_wrapped_rcv_consumed`, plus inherited `_body` / `_stream_consumed` from Request. Constructed eagerly: `self._wrapped_rc_stream = self.stream()` at __init__ (:32).

### Decisive source
```python
# state matrix (in evaluation order)
if disconnected:            return {"type": "http.disconnect"}
if consumed:
    if self._is_disconnected: return {"type": "http.disconnect"}
    msg = await self.receive()          # must be a disconnect now
if getattr(self, "_body", None) is not None:
    return {"type": "http.request", "body": self._body, "more_body": False}   # replay cached body
elif self._stream_consumed:
    return {"type": "http.request", "body": b"", "more_body": False}          # empty-body sentinel
else:
    chunk = await stream.__anext__()    # first real chunk passthrough
```

**Flow:** if dispatch called `request.body()` → downstream gets the WHOLE body as one message; if it called `stream()` → downstream gets empty body + disconnect so nothing hangs; ClientDisconnect mid-read converts to a synthetic `http.disconnect` message instead of raising.
**Invariant:** downstream must NEVER see more body bytes than upstream sent — the empty-body-after-consumption rule exists to prevent deadlocks, not to fake content.
**Probe:** `tests/middleware/test_base.py::test_read_request_body_in_dispatch_after_app_calls_body_with_middleware_calling_body_before_call_next` (:865) and its stream twin (:835) pin both replay branches.

## call_next — task group + memory object stream
**Path/Symbol:** `starlette/middleware/base.py:BaseHTTPMiddleware.__call__` (:101-198) with inner `call_next` (:112-187).
**Data Shape:** `anyio.create_memory_object_stream()` pair; `coro()` runs `self.app(scope, receive_or_disconnect, send_no_error)` in the SAME task group; app messages flow through the stream; exceptions captured into `app_exc` not propagated through the stream.

### Decisive source
```python
async def receive_or_disconnect() -> Message:
    if response_sent.is_set(): return {"type": "http.disconnect"}
    async with anyio.create_task_group() as task_group:
        async def wrap(func):
            result = await func()
            task_group.cancel_scope.cancel()      # first finisher cancels the other
            return result
        task_group.start_soon(wrap, response_sent.wait)
        message = await wrap(wrapped_receive)
    ...
except anyio.EndOfStream:
    if app_exc is not None:
        raise app_exc from app_exc.__cause__ or app_exc.__context__   # de-pollute context
    raise RuntimeError("No response returned.")
```

**Flow:** `send_no_error` swallows BrokenResourceError (downstream stopped listening because dispatch already returned another response); `http.response.debug` messages are skipped over when reading the start message (:152-154) and surface as response extensions; after `dispatch_func` returns, THE RESPONSE IS SENT VIA `wrapped_receive` (not raw receive) so body-replay still works; `response_sent.set()` + stream close unblocks the coro.
**Invariant:** app exceptions must re-raise exactly once (`exception_already_raised` latch :197) with EndOfStream scrubbed from `__context__` — otherwise tracebacks show misleading anyio frames.
**Probe:** `tests/middleware/test_base.py::test_error_context_propagation` (:1262); `::test_app_receives_http_disconnect_while_sending_if_discarded` (:473).

## _StreamingResponse shim
**Path/Symbol:** `starlette/middleware/base.py:_StreamingResponse` (:204-244).
**Data Shape:** wraps the recv side of the stream as an async `body_iterator`; dict chunks (pathsend) pass through verbatim with `should_close_body=False`; raw_headers copied from the start message so header mutation by outer layers survives.
**Probe:** `tests/middleware/test_base.py::test_asgi_pathsend_events` (:1219).

## Get live surrounding code
**Retrieve:**
```ts
// closure: resolve via its containing method and the test anchors that name it
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "wrapped_receive", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", query: "call_next BaseHTTPMiddleware dispatch", limit: 10 });
```
(`call_next` itself is a closure — BM25 has no token for it; retrieve via `wrapped_receive`/`_StreamingResponse` or file range.)

## Verdict
Adopt only if you must support pure `(Request) -> Response` middleware over an ASGI core; prefer native message-passing middleware otherwise. If adopting: keep all three pieces (FSM receive, stream bridge, exception latch) together — they are mutually dependent. Omit the debug-message channel unless you also port TestClient's extension plumbing.
