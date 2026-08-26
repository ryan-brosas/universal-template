<!-- capsule-v2 -->
# View/template/exception middleware side-tables — why does Django run process_view outside the onion and process_exception in reverse?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** If I adopt the onion but need `process_view` / `process_template_response` / `process_exception` hooks, where do they execute relative to the chain and in what order do their lists run?

## Hook side-tables around the chain
**Path/Symbol:** `django/core/handlers/base.py:BaseHandler._get_response` (lines 176–228) with tables built at `load_middleware` :79–95.
**Signature:** `_get_response(self, request)`; hooks: `process_view(request, callback, callback_args, callback_kwargs)`, `process_template_response(request, response)`, `process_exception(request, exception)`.
**Data Shape:** `_view_middleware` (insert(0) during reversed build ⇒ declaration order at run time), `_template_response_middleware` (append during reversed build ⇒ reverse declaration order), `_exception_middleware` (append ⇒ reverse order; always sync-adapted).

### Decisive source
```python
for middleware_method in self._view_middleware:
    response = middleware_method(request, callback, callback_args, callback_kwargs)
    if response:
        break                                    # short-circuit skips the view
if response is None:
    wrapped_callback = self.make_view_atomic(callback)
    ...
    try:
        response = wrapped_callback(request, *callback_args, **callback_kwargs)
    except Exception as e:
        response = self.process_exception_by_middleware(e, request)
        if response is None:
            raise
self.check_response(response, callback)
if hasattr(response, "render") and callable(response.render):
    for middleware_method in self._template_response_middleware:
        response = middleware_method(request, response)
        self.check_response(response, middleware_method, name=...)
    try:
        response = response.render()
    except Exception as e:
        response = self.process_exception_by_middleware(e, request)
        ...
```
and `process_exception_by_middleware` (:358–367): `for m in self._exception_middleware: response = m(request, exception); if response: return response; return None`.

**Flow:** resolve view → run `_view_middleware` in declaration order until one returns a response → call the view (wrapped by `make_view_atomic` when ATOMIC_REQUESTS) → on exception walk `_exception_middleware` (reverse declaration order), first non-None wins, else re-raise into `convert_exception_to_response` → for deferred-render responses run `_template_response_middleware` then render.
**Invariant:** (1) The onion's `__call__` methods see request AND response; these hooks are *outside* the onion — they never wrap each other. (2) A `process_view` returning a response skips the view entirely; a `process_exception` returning falsy passes control to the next handler and ultimately re-raises. (3) `check_response` rejects None or an unawaited coroutine from both views and template-response hooks.
**Probe:** `tests/handlers/tests.py::HandlerRequestTests.test_no_response` (:247) + `tests/handlers/tests.py::AsyncHandlerRequestTests.test_no_response` (:326) — pin the ValueError on views returning None through this path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "_get_response process_view exception middleware", limit: 10 });
```

## Verdict
Adopt the three-side-table decomposition whenever a dispatcher needs pre-view, post-render-shape, and exception phases that plain onion wrapping can't express; adapt hook signatures to your request type; omit ATOMIC_REQUESTS wiring if you have no per-request transactions. Direct tests cited above executed green at this pin.
