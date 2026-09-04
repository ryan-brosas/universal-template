<!-- capsule-v2 -->
# ContextVar-backed globals — why do request/session/g proxies all hang off ONE ContextVar, and when does each unbind?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** How do the five module-level proxies resolve, and what is the exact unbound condition for app-level vs request-level names?

## Proxy ladder over `_cv_app`
**Path/Symbol:** `src/flask/globals.py:33–62` (`_no_app_msg`, `_cv_app`, `app_ctx`, `current_app`, `g`, `request`, `session`).
**Signature:** `LocalProxy(_cv_app)` / `LocalProxy(_cv_app, "app")` / `LocalProxy(_cv_app, "g", unbound_message=...)`.
**Data Shape:** one `ContextVar[AppContext]` named `"flask.app_ctx"`; five `werkzeug.local.LocalProxy` objects. Attribute-name variants delegate to a member of the current AppContext; no-name variants proxy the context object itself.

### Decisive source
```python
_cv_app: ContextVar[AppContext] = ContextVar("flask.app_ctx")
current_app: FlaskProxy = LocalProxy(_cv_app, "app", unbound_message=_no_app_msg)
request: RequestProxy = LocalProxy(_cv_app, "request", unbound_message=_no_req_msg)
```

**Flow:** any attribute access → LocalProxy reads `_cv_app.get()` → None ⇒ UnboundLocalError with the matching message (app message for app_ctx/current_app/g; request message for request/session) → else attribute/member lookup.
**Invariant:** there are NO thread-locals and NO second ContextVar: an unbound `request` can still mean "an app context IS active" — check `has_request_context()` (`ctx.py:209`, `(ctx := _cv_app.get(None)) is not None and ctx.has_request`) rather than truthiness of the proxy in generic code; `if request:` works only because Request implements `__bool__`. A porter who adds a separate request ContextVar breaks `copy_current_request_context`'s single-source copy.
**Probe:** `grep -Fc '_cv_app: ContextVar[AppContext]' src/flask/globals.py` = 1; `tests/test_reqctx.py::test_context_test` (:122) pins has_request/has_app semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "LocalProxy ContextVar current_app request session", limit: 8 });
```

## Verdict
Adopt the one-ContextVar + member-delegating-proxy design (asyncio-safe by construction). Adapt proxy subclass stubs (`FlaskProxy` etc.) which exist only for type checkers. Omit nothing else in this 77-line file.
