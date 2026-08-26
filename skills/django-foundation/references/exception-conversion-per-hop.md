<!-- capsule-v2 -->
# convert_exception_to_response — why is every middleware hop individually exception-proofed, and what happens to each known exception type?

**Source:** django BSD-3-Clause `main@03988c5a5ba248c3b9b11ea96fd4fda5e98849aa`; Codebase Memory `ext-django`. **Question:** Where should a dispatcher guarantee "the next layer always receives a response, never an exception", and how are 404/403/400/500 classified?

## Per-hop exception-to-response conversion
**Path/Symbol:** `django/core/handlers/exception.py:convert_exception_to_response` (25–61) and `response_for_exception` (64–160).
**Signature:** `convert_exception_to_response(get_response)` → sync or async `inner(request)` chosen by `iscoroutinefunction(get_response)`; `response_for_exception(request, exc) -> HttpResponse`.
**Data Shape:** Input: any exception. Output: always an HttpResponse; unclassified exceptions route to `handle_uncaught_exception` (DEBUG technical page or resolver's `handler500`). The async variant converts via `sync_to_async(response_for_exception, thread_sensitive=True)` so the classifier itself stays synchronous.

### Decisive source
```python
if iscoroutinefunction(get_response):
    @wraps(get_response)
    async def inner(request):
        try:
            response = await get_response(request)
        except Exception as exc:
            response = await sync_to_async(
                response_for_exception, thread_sensitive=True)(request, exc)
        return response
    return inner
```
Classification ladder in `response_for_exception`: `Http404` → DEBUG ? `technical_404_response` : `get_exception_response(404)` · `PermissionDenied` → 403 handler + log · `MultiPartParserError` → 400 + log · `BadRequest` → DEBUG technical_500(status_code=400) else 400 · `SuspiciousOperation` (incl. `RequestDataTooBig`, `TooManyFieldsSent`, `TooManyFilesSent`) → `_mark_post_parse_error()` FIRST then 400, logged on `django.security.<ExcName>` · everything else → `got_request_exception` signal + `handle_uncaught_exception`. Tail: force-render any unrendered TemplateResponse before returning.

**Flow:** wrap at EVERY chain build step (both the seed `_get_response` :39 and each middleware instance :97) → on exception classify by isinstance ladder → resolve the URLconf error handler for the status → log with the right logger → force render.
**Invariant:** (1) Because every hop wraps its callee, a middleware can rely on receiving a response rather than an exception — no middleware ever sees another middleware's crash directly. (2) POST-data exceptions must poison the parsed-POST cache (`_mark_post_parse_error`) because re-raising on re-access beats returning stale/partial data. (3) Security events log under per-class `django.security.*` loggers, not `django.request`.
**Probe:** `tests/handlers/tests.py::HandlerRequestTests.test_suspiciousop_in_view_returns_400` (:202) and `.test_bad_request_in_view_returns_400` (:206) — pin SuspiciousOperation→400 and BadRequest→400 through this exact path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-django", query: "convert_exception_to_response response_for_exception", limit: 10 });
```

## Verdict
Adopt the wrap-every-hop discipline and the exception→status taxonomy for any layered server; adapt the status codes/logger names to your domain; omit Django's DEBUG technical pages. Coverage caveat: none — both cited tests executed green at this pin.
