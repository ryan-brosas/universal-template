<!-- capsule-v2 -->
# build_middleware_stack — the canonical two-sentinel onion

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** In what order are user middleware applied, and which two middleware are always present?

## Starlette.build_middleware_stack
**Path/Symbol:** `starlette/applications.py:build_middleware_stack` (:63-83).
**Signature:** `def build_middleware_stack(self) -> ASGIApp`.
**Data Shape:** partitions `self.exception_handlers` — keys `{500, Exception}` become the ServerError `error_handler`, everything else goes to ExceptionMiddleware. List order: `[ServerErrorMiddleware, (RequestBodyLimitMiddleware), *user_middleware, ExceptionMiddleware]`.

### Decisive source
```python
middleware = [Middleware(ServerErrorMiddleware, handler=error_handler, debug=debug)]
if self.max_body_size is not None:
    middleware.append(Middleware(RequestBodyLimitMiddleware, max_body_size=self.max_body_size))
middleware += self.user_middleware
middleware.append(Middleware(ExceptionMiddleware, handlers=exception_handlers, debug=debug))

app = self.router
for cls, args, kwargs in reversed(middleware):
    app = cls(app, *args, **kwargs)
return app
```

**Flow:** the `reversed()` fold means EARLIER list entries end up OUTERMOST — ServerError wraps everything (it must see exceptions from user middleware too), ExceptionMiddleware is innermost (it must wrap only router/endpoint code). Lazy build: `Starlette.__call__` (:92-96) constructs on first request and sets `scope["app"] = self` first; `add_middleware` after that raises RuntimeError.
**Invariant:** user middleware run BETWEEN the two sentinels: they see handled-exception responses from inside but their own exceptions still hit ServerError. A porter who puts user middleware outside ServerError breaks 500 handling for them; one inside ExceptionMiddleware loses exception visibility.
**Probe:** `tests/test_applications.py::test_middleware` (:281) pins ordering; `::test_middleware_stack_init` (:465) pins add-after-start RuntimeError.

## Middleware record + _MiddlewareFactory protocol
**Path/Symbol:** `starlette/middleware/__init__.py:Middleware` (:21-37).
**Data Shape:** `(cls, args, kwargs)` triple that ITERATES as a tuple — this is why every consumer writes the `for cls, args, kwargs in reversed(...)` idiom. `_MiddlewareFactory` protocol types `app` as positional-first with ParamSpec passthrough.
**Invariant:** Router.__init__ and Route.__init__ repeat the same reversed fold for route-level middleware (:609-614, :227-231) — three levels of onion (app → router → route) all compose identically.
**Probe:** `tests/test_routing.py::test_router_middleware` (:317), `::test_base_route_middleware` (:875).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "build_middleware_stack", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "Middleware", limit: 10 });
```

## Verdict
Adopt the sentinel sandwich + reversed-fold + lazy-build contract verbatim. Adapt by inserting your own framework sentinels into the fixed list. Omit nothing — even `max_body_size` insertion order (before user middleware) is deliberate.
