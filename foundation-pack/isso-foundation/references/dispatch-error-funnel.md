<!-- capsule-v2 -->
# Dispatch funnel — how do route misses and handler crashes become responses, and when JSON?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `isso`. **Question:** Where do thread-locals get set and which errors reach the client as JSON vs HTML?

## Isso.dispatch + error_handler
**Path/Symbol:** `isso/__init__.py:Isso.dispatch` (:135-156), `error_handler` (:81-86), `wsgi_app`/`__call__` (:158-163).
**Signature:** `dispatch(request) -> Response`; `error_handler(env, request, error) -> JSONResponse | HTTPException`.
**Data Shape:** every request enters as `JSONRequest(environ)`; thread-locals `local.request/local.host/local.origin` are set BEFORE routing.

### Decisive source
```python
def error_handler(env, request, error):
    if request.accept_mimetypes.best == "application/json":
        data = {"message": str(error)}
        code = 500 if error.code is None else error.code
        return JSONResponse(data, code)
    return error                      # pass-through: werkzeug renders the HTML page

def dispatch(self, request):
    local.request = request
    local.host = wsgi.host(request.environ)      # PEP-333 reconstruction + SCRIPT_NAME
    local.origin = origin(self.conf.getiter("general", "host"))(request.environ)
    adapter = self.urls.bind_to_environ(request.environ)
    try:
        handler, values = adapter.match()
    except HTTPException as e:
        return error_handler(request.environ, request, e)
    else:
        try:
            response = handler(request.environ, request, **values)
        except HTTPException as e:
            return error_handler(request.environ, request, e)
        except Exception:
            logger.exception("%s %s", request.method, request.environ["PATH_INFO"])
            return error_handler(request.environ, request, InternalServerError())
```

**Flow:** set thread-locals → bind the werkzeug `Map` to the environ → on match failure OR handler-raised HTTPException hand the exception to `error_handler`; on ANY other exception log the full traceback server-side and synthesize `InternalServerError()` so clients never see stack details. `local.host` (single producer: this line; consumers: `isso/views/comments.py:487,1478,1489,1525` as `public-endpoint or local.host` for absolute URLs).
**Invariant:** JSON is emitted ONLY when the client's best accepted MIME is exactly `application/json` — browsers (`text/html` preferred) receive the exception object itself. A missing `error.code` maps to 500. The traceback goes to logs, never to the response.
**Probe:** direct test pins all three arms — see Probe/test below; byte check `grep -c 'InternalServerError())' isso/__init__.py` → `1`.
**Test:** `isso/tests/test_wsgi.py:test_errorhandler` (:47-83): HTML-preferred ⇒ identity return of the BadRequest CLASS; JSON-preferred ⇒ JSONResponse with status retained (400); `error.code = None` ⇒ status 500 and message `"??? Unknown Error: invalid data"`; no Accept header ⇒ `best is None`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "isso", query: "dispatch error_handler accept_mimetypes InternalServerError bind_to_environ", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-funnel error path with accept-negotiated serialization and server-only tracebacks. Adapt the MIME predicate to your content types. Omit the thread-local host/origin split if your framework already scopes per-request state.
