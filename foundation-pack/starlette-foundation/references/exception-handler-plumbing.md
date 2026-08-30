<!-- capsule-v2 -->
# Exception handler plumbing — MRO lookup, scope-injected tables, response-started latch

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How do user exception handlers get found at throw time, and what are the two ways an unhandled error still surfaces?

## _lookup_exception_handler + wrap_app_handling_exceptions
**Path/Symbol:** `starlette/_exception_handler.py:_lookup_exception_handler` (:16-20), `:wrap_app_handling_exceptions` (:23-65).
**Signature:** `wrap_app_handling_exceptions(app: ASGIApp, conn: Request | WebSocket) -> ASGIApp`.
**Data Shape:** handler tables come from `conn.scope["starlette.exception_handlers"]` (a tuple `(exception_handlers, status_handlers)` injected by ExceptionMiddleware); missing key → empty tables (standalone mode). Lookup order for an HTTPException: `status_handlers[exc.status_code]` FIRST, then MRO walk of `type(exc)`.

### Decisive source
```python
async def sender(message: Message) -> None:
    nonlocal response_started
    if message["type"] == "http.response.start":
        response_started = True
    await send(message)

...
except Exception as exc:
    ...
    if response_started:
        raise RuntimeError("Caught handled exception, but response already started.") from exc
    if is_async_callable(handler):
        response = await handler(conn, exc)
    else:
        response = await run_in_threadpool(handler, conn, exc)
    if response is not None:
        await response(scope, receive, sender)
```

**Flow:** the sender shim tracks whether ANY bytes were committed; a handled exception after that point becomes RuntimeError (you cannot 500 mid-stream); handlers run sync-in-threadpool like endpoints; a handler returning None sends nothing (websocket close handlers).
**Invariant:** only `Exception` is caught — BaseException (CancelledError on anyio backends, KeyboardInterrupt) propagates untouched. The wrapper never logs; logging is ServerErrorMiddleware's job.
**Probe:** `tests/test_exceptions.py` (14 tests pin MRO precedence incl. subclass-vs-status conflicts).

## ExceptionMiddleware — table installation + built-ins
**Path/Symbol:** `starlette/middleware/exceptions.py:ExceptionMiddleware.__call__` (:47-63), `http_exception` (:65-69).
**Data Shape:** installs `(self._exception_handlers, self._status_handlers)` into the scope then delegates through `wrap_app_handling_exceptions`; seeds tables with `HTTPException → http_exception` and `WebSocketException → websocket_exception`.
**Flow:** `http_exception` renders `PlainTextResponse(exc.detail, exc.status_code, exc.headers)` EXCEPT for `{204, 304}` where body-bearing responses are illegal (`Response(status_code=...)`, no body).
**Probe:** `tests/test_applications.py::test_400` (:218) pins detail rendering; `tests/middleware/test_errors.py::test_handler` parametrized pins 204/304.

## ServerErrorMiddleware — the outermost 500 net
**Path/Symbol:** `starlette/middleware/errors.py:ServerErrorMiddleware.__call__` (:149-186).
### Decisive source
```python
if not response_started:
    await response(scope, receive, send)   # debug traceback | user 500 handler | plain text
# We always continue to raise the exception.
raise exc
```
**Flow:** builds its OWN `_send` started-tracker (independent of route-level ones); picks response by ladder `debug_response` (HTML if Accept: text/html else full plain-text traceback via `traceback.TracebackException.from_exception(capture_locals=True)`) → user `handler` → `error_response` ("Internal Server Error"); ALWAYS re-raises afterward so servers log it / TestClient can assert. Non-http scopes pass straight through.
**Invariant:** re-raise-after-respond means downstream sees BOTH a complete 500 response AND the exception; test clients with `raise_server_exceptions=True` turn this into test failures.
**Probe:** `tests/middleware/test_errors.py::test_debug_text` (:31), `::test_debug_html` (:43), `::test_debug_after_response_sent` (:55), `::test_not_http` (:67); `tests/test_applications.py::test_500` (:234).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "wrap_app_handling_exceptions", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "_lookup_exception_handler", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "http_exception", limit: 5 });
```

## Verdict
Adopt the two-table (status/class) scheme, MRO walk, response-started RuntimeError, and always-re-raise outer middleware — together they form one contract; porting half of it produces silent double-responses. Adapt the debug traceback renderer per your HTML policy. Omit `capture_locals=True` in production ports (memory exposure).
