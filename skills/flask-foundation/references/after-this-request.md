<!-- capsule-v2 -->
# after_this_request — how does a view register a one-shot response hook?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** Where is the per-request hook stored and when does it run relative to blueprint after_request funcs?

## ctx._after_request_functions injection
**Path/Symbol:** `src/flask/ctx.py:after_this_request` (118–148); consumed by `src/flask/app.py:Flask.process_response` (1397–1421).
**Signature:** `after_this_request(f) -> f`; requires an active context WITH request (`ctx.has_request`) else RuntimeError.
**Data Shape:** appends to `ctx._after_request_functions: list[AfterRequestCallable]` — lives on the CONTEXT, not the app.

### Decisive source
```python
ctx = _cv_app.get(None)
if ctx is None or not ctx.has_request:
    raise RuntimeError(...)
ctx._after_request_functions.append(f)

# process_response:
for func in ctx._after_request_functions:      # FIRST
    response = self.ensure_sync(func)(response)
for name in chain(ctx.request.blueprints, (None,)):   # then bp innermost→app, REVERSED
    if name in self.after_request_funcs:
        for func in reversed(self.after_request_funcs[name]):
            response = self.ensure_sync(func)(response)
```

**Flow:** register inside view → finalize_request → make_response → process_response runs one-shots before the global chain → context dies with the request so the list never persists.
**Invariant:** one-shots run even though they were registered mid-view; they do NOT survive redirects handled by the test client's context preservation unless the context itself is preserved; session save happens AFTER all of these.
**Probe:** `grep -Fc 'or not ctx.has_request' src/flask/ctx.py` = 1; `grep -Fc 'session["_flashes"]' src/flask/helpers.py` = 0 (distinct seam); ordering pinned by `tests/test_blueprints.py::test_nested_callback_order` (:911).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "process_response after_request order", limit: 6 });
```

## Verdict
Adopt per-context hook lists drained before global chains. Adapt naming. Omit nothing.
