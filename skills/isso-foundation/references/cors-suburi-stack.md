<!-- capsule-v2 -->
# CORS + SubURI middleware stack — how is the WSGI pipeline ordered for embeddable apps?

**Source:** isso MIT `master@5ad388d9f10cc5227f6e5d901c249ca888f5ef72`; Codebase Memory `ext-isso`. **Question:** What wrappers wrap the app, in what order, and what does each contribute?

## make_app wrapper chain
**Path/Symbol:** `isso/__init__.py:make_app` (lines 204–232); middlewares `isso/wsgi.py:CORSMiddleware/SubURI` (92–134).
**Signature:** `reduce(lambda x, f: f(x), wrapper, isso)` with wrapper = [local_manager, (profiler), SharedDataMiddleware, CORSMiddleware, SubURI, ProxyFixCustom].
**Data Shape:** CORS allowed headers = Origin/Referer/Content-Type; exposed = X-Set-Cookie/Date; OPTIONS short-circuits to `200 OK` with `[]`.

### Decisive source
```python
def add_cors_headers(status, headers, exc_info=None):
    headers = Headers(headers)
    headers.add("Access-Control-Allow-Origin", self.origin(environ))
    headers.add("Access-Control-Allow-Credentials", "true")
    ...
    return start_response(status, headers.to_wsgi_list(), exc_info)

if environ.get("REQUEST_METHOD") == "OPTIONS":
    add_cors_headers("200 OK", [("Content-Type", "text/plain")])
    return []

# SubURI: rewrite when hosted under a path prefix
script_name = environ.get("HTTP_X_SCRIPT_NAME")
if script_name:
    environ["SCRIPT_NAME"] = script_name
    path_info = environ["PATH_INFO"]
    if path_info.startswith(script_name):
        environ["PATH_INFO"] = path_info[len(script_name):]
```

**Flow:** innermost app → LocalManager (request-scoped `local`) → optional Profiler → SharedDataMiddleware serving /js /css /img /demo from the package → CORS (per-request origin echo from allowlist; preflight answered WITHOUT calling the app) → SubURI (strip configured prefix) → ProxyFixCustom (`x_prefix=1` so get_current_url works under sub-paths). CORS headers are injected by REPLACING start_response — every downstream response gains them.
**Invariant:** Middleware order matters: CORS wraps SubURI so preflights are answered even before prefix handling; credentials-true CORS requires the exact allowlisted origin (see origin-negotiation capsule).
**Probe:** `grep -c HTTP_X_SCRIPT_NAME isso/wsgi.py` (`1`); `grep -c x_prefix=1 isso/__init__.py` (`1`).
**Test:** `isso/tests/test_cors.py:test_simple`, `test_preflight`; `test_wsgi.py:test_errorhandler`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-isso", query: "CORSMiddleware SubURI ProxyFix make_app wrapper", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordering template for any cross-origin embeddable widget backend. Adapt exported headers. Keep OPTIONS short-circuit before auth-bearing middleware.
