<!-- capsule-v2 -->
# Merged app/request context — how does ONE context serve both app-only and request work without re-push detection?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** How are app and request contexts unified in one object, and what must a porter preserve when pushing/popping it?

## AppContext push/pop state machine
**Path/Symbol:** `src/flask/ctx.py:AppContext` (300–525), `_AppCtxGlobals` (30–115).
**Signature:** `AppContext(app, *, request=None, session=None)`; `.push() -> None`; `.pop(exc=None) -> None`; `.copy() -> te.Self`; `has_request -> bool`.
**Data Shape:** holds `app`, `g` (`_AppCtxGlobals` namespace), `url_adapter` (MapAdapter|None, built in `__init__` — a routing failure is stored on the request as `routing_exception`, NOT raised), `_request`, `_session` (lazy!), `_flashes` cache, `_after_request_functions`, plus two bookkeeping fields: `_cv_token` (contextvars token) and `_push_count`.

### Decisive source
```python
def push(self) -> None:
    self._push_count += 1
    if self._cv_token is not None:
        return                      # already pushed; nested pushes only bump count
    self._cv_token = _cv_app.set(self)
    ...
    if self._request is not None:
        self._get_session()         # session opened HERE, lazily at push time
        if self.url_adapter is not None:
            self.match_request()    # routing runs with session available

def pop(self, exc=None) -> None:
    ...
    self._push_count -= 1
    if self._push_count > 0:
        return                      # cleanup deferred until outermost pop
```

**Flow:** construct (build url adapter; routing errors parked on request) → push (token set once, count incremented; session opened BEFORE match so custom converters can read session) → nested push (count bump only) → pop decrements → at zero: request teardown funcs → `request.close()` → appcontext teardown funcs → reset ContextVar → popped signal → `raise_any`.
**Invariant:** cleanup runs exactly ONCE per context even after N pushes; session access happens before URL matching; `pop()` of a non-active context raises RuntimeError.
**Probe:** `grep -Fc '_cv_token = _cv_app.set(self)' src/flask/ctx.py` = 1; `tests/test_reqctx.py::test_teardown_on_pop` (:15) and `tests/test_appctx.py::test_robust_teardown` (:216) pin teardown-once behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "AppContext push pop teardown", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the single merged context + `_push_count`/`_cv_token` pair and lazy-session-then-match ordering (3.2 semantics; pre-3.2 separate RequestContext detection code is obsolete). Adapt `g` storage class via `app_ctx_globals_class`. Omit the `RequestContext` alias shim (removed in Flask 4.0). Coverage caveat: none — file fully indexed.
