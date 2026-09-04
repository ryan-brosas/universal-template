<!-- capsule-v2 -->
# Dual exit-stack lifecycle — Where do request-scoped vs function-scoped dependency teardowns run, and what breaks if a bare except swallows the endpoint error?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** With dependencies that use `yield`, when exactly does teardown code run relative to response sending, and how does FastAPI detect the swallowed-exception bug?

## Three stacked AsyncExitStacks
**Path/Symbol:** `fastapi/routing.py:request_response` (lines 121–160; inner app 134–155); stacks consumed in `fastapi/dependencies/utils.py:solve_dependencies` (601–608) and `get_request_handler.app` (477–488); middleware stack in `fastapi/middleware/asyncexitstack.py` (whole file, 18L).
**Signature:** scope keys: `fastapi_middleware_astack`, `fastapi_inner_astack` (request-scoped deps), `fastapi_function_astack` (function-scope deps).
**Data Shape:** generator dependencies are entered via `_solve_generator` → `asynccontextmanager(call)(**sub_values)` for async gens, `contextmanager_in_threadpool(contextmanager(call)(**sub_values))` for sync gens — chosen by scope at solve time (`scope == "function"` ⇒ function stack).

### Decisive source
```python
        async def app(scope, receive, send) -> None:
            response_awaited = False
            async with AsyncExitStack() as request_stack:
                scope["fastapi_inner_astack"] = request_stack
                async with AsyncExitStack() as function_stack:
                    scope["fastapi_function_astack"] = function_stack
                    response = await f(request)
                await response(scope, receive, send)      # AFTER function stack closed,
                response_awaited = True                   # INSIDE request stack still open
            if not response_awaited:
                raise FastAPIError(
                    "Response not awaited. There's a high chance that the "
                    "application code is raising an exception and a dependency with yield "
                    "has a block with a bare except, or a block with except Exception, "
                    "and is not raising the exception again. Read more about it in the "
                    "docs: .../dependencies-with-yield/#dependencies-with-yield-and-except"
                )
```

**Flow:** endpoint runs inside function-stack context → function-scope dep teardowns run BEFORE the response is sent (can set headers/status via the injected `Response`) → response is sent while REQUEST-scope yield-deps are still open → request-scope teardowns (DB sessions etc.) close after the client has the bytes; files opened from form parsing close via the third `fastapi_middleware_astack`.
**Invariant:** (1) The `response_awaited` latch only becomes True after `response(...)` returns; an exception raised inside `f(request)` normally skips it — but if a yield-dep's teardown catches the exception with a bare `except` without re-raising, unwinding completes "normally", the flag check fires, and the user gets the explicit FastAPIError instead of silent truncation. (2) A second registration of the same scope key would nest-clobber; keys live on the request `scope` dict so sub-apps each install their own.
**Probe:** `tests/test_dependency_after_yield_raise.py` / `tests/test_dependency_after_yield_streaming.py` / `tests/test_dependency_after_yield_websockets.py` — pin teardown ordering and the raise-through-yield behavior; `request_response`'s guard is the observable boundary for the swallowed-exception case.
