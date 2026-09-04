<!-- capsule-v2 -->
# Validation exception context — How do 422/500 validation errors carry endpoint file/line context, and how is it extracted cheaply?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** What extra diagnostics do `RequestValidationError` / `ResponseValidationError` carry beyond pydantic errors, and what does the default handler emit?

## EndpointContext capture + error envelope
**Path/Symbol:** `fastapi/routing.py:_extract_endpoint_context` (278–298, id-keyed cache at 275) + `fastapi/exceptions.py:ValidationException` (174–209) + `fastapi/exception_handlers.py` (whole, 34L).
**Signature:** `_extract_endpoint_context(func) -> EndpointContext` (TypedDict: function/path/file/line); handlers: `async def request_validation_exception_handler(request, exc) -> JSONResponse` etc.
**Data Shape:** ctx enriched per request with `"path": f"{request.method} {mount_path}{dependant.path}"` (routing.py 420–423); WS variant uses `"WS {mount}{path}".`

### Decisive source
```python
def _extract_endpoint_context(func):
    func_id = id(func)
    if func_id in _endpoint_context_cache:
        return _endpoint_context_cache[func_id]
    try:
        ctx: EndpointContext = {}
        if (source_file := inspect.getsourcefile(func)) is not None:
            ctx["file"] = source_file
        if (line_number := inspect.getsourcelines(func)[1]) is not None:
            ctx["line"] = line_number
        if (func_name := getattr(func, "__name__", None)) is not None:
            ctx["function"] = func_name
    except Exception:
        ctx = EndpointContext()
    _endpoint_context_cache[func_id] = ctx
    return ctx
```
handler:
```python
async def request_validation_exception_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": jsonable_encoder(exc.errors())})
```

**Flow:** source introspection happens ONCE per endpoint callable (module-level dict keyed by `id(func)` — safe because endpoint functions live for the process lifetime) and is attached to every RequestValidationError / WebSocketRequestValidationError / ResponseValidationError → `__str__` renders a traceback-style block (`File "...", line N, in fn` + endpoint path) so server LOGS point at the failing operation even when the client only sees `{"detail": [...]}`.
**Invariant:** (1) The cache is essential — `inspect.getsourcelines` does file I/O and would otherwise run per request. (2) Client payloads stay unchanged (`detail` list only); the context is for operators via str/logs. (3) All three validation exceptions share one base whose `errors()` returns the ORIGINAL sequence — porters must not re-serialize into strings before logging.
**Probe:** `tests/test_local_exceptions.py` pins message formatting; response-shape suites (e.g. `tests/test_multi_body_errors.py`) pin the 422 body.
