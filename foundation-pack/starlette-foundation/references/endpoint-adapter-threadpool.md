<!-- capsule-v2 -->
# request_response/websocket_session adapters — sync endpoints without blocking the loop

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How does a plain `def endpoint(request) -> Response` become an ASGI app, and where exactly must exception handling wrap?

## request_response
**Path/Symbol:** `starlette/routing.py:request_response` (:47-67).
**Signature:** `(func: Callable[[Request], Awaitable[Response] | Response]) -> ASGIApp`.
**Data Shape:** async check via `is_async_callable` (partial-unwrapping); sync functions are wrapped as `functools.partial(run_in_threadpool, func)` — the threadpool hop happens per call.

### Decisive source
```python
async def app(scope: Scope, receive: Receive, send: Send) -> None:
    request = Request(scope, receive, send)

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        response = await f(request)
        await response(scope, receive, send)

    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
```

**Flow:** the Request object is built ONCE and closed over; the inner app runs the endpoint + sends the response; the exception wrapper is applied at the ROUTE level (not the app level), which is why HTTPException raised in any route handler renders even when the router is mounted standalone-but-with-app.
**Invariant:** `is_async_callable` must see through `functools.partial` — a naive `iscoroutinefunction` misclassifies partial-wrapped async endpoints into the threadpool. The inner closure re-declares `(scope, receive, send)` because `wrap_app_handling_exceptions` passes ITS OWN sender (response-started tracker).
**Probe:** `tests/test_routing.py::test_partial_async_endpoint` (:730) pins the partial-async classification.

## websocket_session
**Path/Symbol:** `starlette/routing.py:websocket_session` (:70-86).
**Flow:** identical shape with `WebSocket(scope, receive=receive, send=send)` created once and shared across the whole session; exceptions from the handler flow through the same wrapper (so WebSocketException → close).
**Probe:** `tests/test_routing.py::test_partial_async_ws_endpoint` (:741).

## Endpoint classification twin
**Path/Symbol:** `starlette/routing.py:Route.__init__` (:215-226) — strips `functools.partial` layers then `inspect.isfunction/ismethod`: function/method → `request_response(endpoint)` + default methods `["GET"]`; anything else (class instance) used AS the ASGI app verbatim. WebSocketRoute repeats it (:311-319) WITHOUT a default-methods branch.
**Invariant:** class-based endpoints get NO implicit method filter — they implement `matches/handle/__call__` semantics themselves.
**Probe:** `tests/test_routing.py::test_route_name` parametrized (:795) covers function/partial/class naming; `::test_standalone_route_matches` (:580).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "request_response", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "websocket_session", limit: 5 });
```

## Verdict
Adopt the adapter pattern (sync→threadpool, one Request per route invocation, wrapper-at-route-level). Adopt `is_async_callable`'s partial-unwrapping loop (`starlette/_utils.py:42-46`) as-is — it's 4 lines and load-bearing everywhere.
