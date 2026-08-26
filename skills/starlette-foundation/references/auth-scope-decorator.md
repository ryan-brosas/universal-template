<!-- capsule-v2 -->
# Authentication requires() decorator — scope gate with request/websocket param discovery

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How does one decorator cover sync/async/WS endpoints, and where does the redirect-vs-403 decision live?

## AuthenticationMiddleware — backend protocol + WS error path
**Path/Symbol:** `starlette/middleware/authentication.py:AuthenticationMiddleware.__call__` (:29-48).
**Data Shape:** backend returns `tuple[AuthCredentials, BaseUser] | None`; None → `(AuthCredentials(), UnauthenticatedUser())` (anonymous, not error). On AuthenticationError: http → on_error response; websocket → bare `websocket.close(code=1000)`.
**Flow:** writes `scope["auth"], scope["user"]` which HTTPConnection properties surface with assert-messages naming the required middleware.
**Probe:** `tests/test_authentication.py::test_custom_on_error` (:347), `::test_websocket_authentication_required` (:273).

## requires() — three wrappers off one signature scan
**Path/Symbol:** `starlette/authentication.py:requires` (:25-98) + `has_required_scope` (:18-22).
### Decisive source
```python
sig = inspect.signature(func)
for idx, parameter in enumerate(sig.parameters.values()):
    if parameter.name == "request" or parameter.name == "websocket":
        type_ = parameter.name; break
else:
    raise Exception(f'No "request" or "websocket" argument on function "{func}"')
```
**Flow:** positional index OR kwarg (`kwargs.get("request", args[idx] if idx < len(args) else None)`) resolves the connection at call time; failure ladder for http: `redirect` given → RedirectResponse(url_for(redirect) + "?next=" + urlencode(current url), 303); else HTTPException(status_code=403 default). Websockets just close().
**Invariant:** the decorator asserts the resolved object's TYPE (Request/WebSocket) — protects against frameworks passing connections positionally in unexpected slots.
**Probe:** `::test_invalid_decorator_usage` (:204), `::test_authentication_redirect` (:306).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "requires", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "has_required_scope", limit: 5 });
```

## Verdict
Adopt the param-scan + triple-wrapper pattern for any endpoint-level policy decorator. Adapt scopes to your auth model (the check is a flat list membership test). Omit redirect flow if your frontend handles 401s client-side.
