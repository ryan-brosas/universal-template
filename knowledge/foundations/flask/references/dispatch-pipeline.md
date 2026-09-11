<!-- capsule-v2 -->
# Dispatch pipeline — in what order do preprocess, view, finalize, and the three exception tiers run?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** How does a request flow through before/after hooks and how are HTTP, user, and unhandled exceptions classified?

## full_dispatch → handle_user/http/exception tiering
**Path/Symbol:** `src/flask/app.py:Flask.full_dispatch_request` (995–1022), `.preprocess_request` (1369–1395), `.dispatch_request` (969–993), `.finalize_request` (1024–1054), `.handle_http_exception` (833–866), `.handle_user_exception` (868–898), `.handle_exception` (900–951).
**Signature:** `full_dispatch_request(ctx) -> Response`; `preprocess_request(ctx) -> ResponseReturnValue|None`; `dispatch_request(ctx) -> ResponseReturnValue`.
**Data Shape:** preprocess returns None or a short-circuit value; dispatch returns any view value; `_find_error_handler(e, blueprints)` resolves handler tables keyed `{scope: {code: {exc_class: fn}}}`.

### Decisive source
```python
try:
    request_started.send(self, _async_wrapper=self.ensure_sync)
    rv = self.preprocess_request(ctx)
    if rv is None:
        rv = self.dispatch_request(ctx)
except Exception as e:
    rv = self.handle_user_exception(ctx, e)
return self.finalize_request(ctx, rv)
```
`dispatch_request`: routing_exception → `raise_routing_exception`; rule with `provide_automatic_options` + OPTIONS ⇒ default OPTIONS response; else `self.view_functions[rule.endpoint](**view_args)`.

**Flow:** signal → url_value_preprocessors then before_request funcs over `(None, *reversed(req.blueprints))` — first non-None return short-circuits the view → view → make_response → after_request chain (per-request `_after_request_functions` first, then blueprint scope innermost-first, each REVERSED) → save_session unless null session. Exceptions: HTTPException with code → handler-or-self; RoutingException passthrough (internal redirects); no-handler user exception re-raises into `handle_exception`, which sends got_request_exception and either propagates (`PROPAGATE_EXCEPTIONS` None ⇒ testing or debug) or wraps in `InternalServerError(original_exception=e)` and finalizes with `from_error_handler=True` so a failing error path logs instead of raising.
**Invariant:** teardown is NOT here — it lives in ctx.pop; after-request funcs are skipped when an exception escapes (only finalize from error handlers runs); OPTIONS auto-response fires only when the matched RULE opted in.
**Probe:** `grep -Fc 'return self.make_default_options_response(ctx)' src/flask/app.py` = 1; `grep -Fc 'isinstance(e, RoutingException)' src/flask/app.py` = 1; `tests/test_basic.py::test_errorhandler_precedence` (:1021), `tests/test_basic.py::test_before_after_request_order` (:851).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "full_dispatch_request handle_exception propagate", limit: 8 });
```

## Verdict
Adopt the three-tier classification and reversed after-chain ordering. Adapt `ensure_sync` to your async story (asgiref wrapper behind the `async` extra). Omit the deprecated `should_ignore_error` warning block.
