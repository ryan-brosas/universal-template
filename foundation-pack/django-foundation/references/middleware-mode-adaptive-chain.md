<!-- capsule-v2 -->
# Middleware mode-adaptive chain — how does Django build one call stack that mixes sync and async middleware without deadlocking or thread-hopping?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** When porting a middleware/onion dispatcher that supports both sync and async handlers, where exactly do the sync↔async adapters get installed and what decides each hop's mode?

## Mode-adaptive middleware chain builder
**Path/Symbol:** `django/core/handlers/base.py:BaseHandler.load_middleware` (lines 27–104) + `adapt_method_mode` (106–136).
**Signature:** `load_middleware(self, is_async=False)`; `adapt_method_mode(self, is_async, method, method_is_async=None, debug=False, name=None)`.
**Data Shape:** `settings.MIDDLEWARE` list of dotted paths; builds `_middleware_chain` plus three side tables `_view_middleware`, `_template_response_middleware`, `_exception_middleware`; `is_async` flag comes from the handler subclass (`ASGIHandler.__init__` → `load_middleware(is_async=True)`, `WSGIHandler` → default False).

### Decisive source
```python
for middleware_path in reversed(settings.MIDDLEWARE):        # build innermost-first
    middleware_can_sync = getattr(middleware, "sync_capable", True)
    middleware_can_async = getattr(middleware, "async_capable", False)
    if not middleware_can_sync and not middleware_can_async:
        raise RuntimeError(...)                               # must be at least one
    elif not handler_is_async and middleware_can_sync:
        middleware_is_async = False                           # stay sync if possible
    else:
        middleware_is_async = middleware_can_async            # else adopt async
    adapted_handler = self.adapt_method_mode(middleware_is_async, handler,
                                             handler_is_async, ...)
    mw_instance = middleware(adapted_handler)
    ...
    handler = convert_exception_to_response(mw_instance)
    handler_is_async = middleware_is_async
# Adapt the top of the stack, if needed.
handler = self.adapt_method_mode(is_async, handler, handler_is_async)
self._middleware_chain = handler      # assigned LAST = init-complete flag
```
`adapt_method_mode`: async target + sync method ⇒ `sync_to_async(method, thread_sensitive=True)`; sync target + async method ⇒ `async_to_sync(method)`; mode detection via `iscoroutinefunction` when `method_is_async is None`.

**Flow:** iterate MIDDLEWARE **reversed** → per-hop capability negotiation (`sync_capable` defaults True, `async_capable` defaults False) → adapt the *inner* handler to the middleware's chosen mode → instantiate factory with adapted handler → wrap instance in `convert_exception_to_response` → record its mode for the next hop → final top-of-stack adaptation to the entrypoint's mode.
**Invariant:** (1) A hop runs async only if the middleware declares `async_capable` AND the current chain is already async — a sync-capable middleware on a sync chain never pays a thread hop; adapters are inserted ONLY at genuine mode boundaries. (2) `process_exception` is always adapted to sync (`adapt_method_mode(False, ...)`) because the exception stack is still synchronous-only. (3) `_middleware_chain` is assigned only after full success, doubling as the initialization-complete flag.
**Probe:** `tests/middleware/tests.py` + `tests/middleware_exceptions/tests.py::MiddlewareSyncAsyncTests` (:237, incl. `test_async_and_sync_middleware_chain_async_call` :217) — pin async/sync mixing and `MiddlewareNotUsed` skipping (the `continue` leaves `handler` unchanged so a skipped middleware contributes no adapter).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "load_middleware adapt_method_mode middleware chain", limit: 10 });
```

## Verdict
Adopt the reversed-build + per-hop mode negotiation + boundary-only adaptation pattern verbatim for any dual-mode dispatcher; adapt the adapter primitives (`asgiref.sync.sync_to_async/async_to_sync`) to your runtime's equivalents; omit Django's settings plumbing. Coverage caveat: behavior is pinned by the two test modules cited above, executed at this pin.
