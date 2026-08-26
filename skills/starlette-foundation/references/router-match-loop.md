<!-- capsule-v2 -->
# Router match loop — how does a request find its route, and what happens on the way?

**Source:** Starlette BSD-3-Clause `main@675ae76855d3d09f5a4493c15ad321a3cd02390d`; Codebase Memory `ext-starlette`. **Question:** When porting the router, in what order are routes tried, what survives into the child scope, and why does a 404 sometimes raise instead of returning?

## Router.app — full-then-partial two-pass dispatch
**Path/Symbol:** `starlette/routing.py:Router.app` (:672-722).
**Signature:** `async def app(self, scope: Scope, receive: Receive, send: Send) -> None`.
**Data Shape:** iterates `self.routes` calling each route's `matches(scope)` → `(Match, child_scope)`; keeps the FIRST `Match.PARTIAL` (`partial`, `partial_scope`) but only dispatches it after the whole list is exhausted.

### Decisive source
```python
for route in self.routes:
    match, child_scope = route.matches(scope)
    if match == Match.FULL:
        scope["route"] = route
        scope.update(child_scope)
        await route.handle(scope, receive, send)
        return
    elif match == Match.PARTIAL and partial is None:
        partial = route
        partial_scope = child_scope

if partial is not None:
    scope["route"] = partial
    scope.update(partial_scope)
    await partial.handle(scope, receive, send)   # 405 path
```

**Flow:** FULL wins immediately (first-match-wins registration order) and mutates the scope in place with `route` + merged `path_params` + `endpoint` → `route.handle`. Only when NO route fully matches does the first PARTIAL (path matched, method didn't) handle the request, producing 405. Otherwise slash-redirection: if `redirect_slashes` and `route_path != "/"`, re-run matching against a scope whose `path` gained/lost a trailing slash; if anything matches (even PARTIAL), send `RedirectResponse` (307). Last resort `self.default` = `not_found`.
**Invariant:** `Match.PARTIAL` must never short-circuit a later FULL match — collect, don't dispatch. The 405 response's `Allow` header comes from `Route.handle`, so the partial route chosen must be the first path-matching one.
**Probe:** `tests/test_routing.py::test_router` (:181) pins first-match-wins + `/404` fallback; `tests/test_applications.py::test_405` (:224) pins method-not-allowed via partial.

## Router.not_found — raise-or-return duality
**Path/Symbol:** `starlette/routing.py:Router.not_found` (:616-629).
**Data Shape:** websocket → `WebSocketClose()` message (no exception); http inside a Starlette app (`"app" in scope`) → `raise HTTPException(404)` so the ExceptionMiddleware handler renders it; bare ASGI → returns `PlainTextResponse("Not Found", 404)` directly.

**Flow:** the same router serves both embedded (Starlette app, handlers installed) and standalone (raw ASGI, no handlers) contexts; only the former can rely on `scope["starlette.exception_handlers"]` existing.
**Invariant:** A porter that always raises breaks standalone-router usage; one that always returns loses the user-configurable 404 handler.
**Probe:** `tests/test_routing.py::test_standalone_route_does_not_match` (:590).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "not_found", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "matches", limit: 20 }); // Route/WebSocketRoute/Mount/Host variants
```

## Verdict
Adopt the two-pass full→partial loop and the scope keys it writes (`route`, `endpoint`, `path_params`). Adopt the raise-vs-return 404 split keyed on `"app" in scope`. Adapt `redirect_slashes` if your framework treats trailing slashes as distinct routes. Omit the deprecated `add_route`/`mount`/`host` convenience methods (:727-759, pragma no cover).
