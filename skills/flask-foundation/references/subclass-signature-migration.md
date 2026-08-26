<!-- capsule-v2 -->
# Subclass signature migration — how does Flask 3.2 keep old `handle_*`/dispatch overrides working without the ctx arg?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What do the add_ctx/remove_ctx wrappers inspect, and what annotation forms count as migrated?

## __init_subclass__ deprecation shims
**Path/Symbol:** `src/flask/app.py:Flask.__init_subclass__` (255–309); helpers `remove_ctx` (86–93) / `add_ctx` (98–107).
**Signature:** wraps overridden methods at subclass-CREATION time; detection via `inspect.signature` second parameter.
**Data Shape:** guarded method list: handle_http_exception, handle_user_exception, handle_exception, log_exception, dispatch_request, full_dispatch_request, finalize_request, make_default_options_response, preprocess_request, process_response, do_teardown_request, do_teardown_appcontext.

### Decisive source
```python
iter_params = iter(inspect.signature(method).parameters.values())
next(iter_params)                       # skip self
param = next(iter_params, None)
if param is None or not (
    (param.annotation is inspect.Parameter.empty and param.name == "ctx")   # name only
    or (isinstance(param.annotation, str)
        and param.annotation.rpartition(".")[2] == "AppContext")             # string ann
    or (inspect.isclass(param.annotation)
        and issubclass(param.annotation, AppContext))                       # class ann
):
    warnings.warn("The '...' method now takes 'ctx: AppContext' ...", DeprecationWarning)
    setattr(cls, method.__name__, remove_ctx(method))   # strip ctx when calling user code
    setattr(Flask, method.__name__, add_ctx(base_method))  # inject ctx into base calls
```

**Flow:** class definition of a Flask subclass triggers inspection → unmigrated overrides wrapped so they still receive `(self, e)`-style args; their calls UP to super() get a context injected from the current app_ctx.
**Invariant:** the shim mutates BOTH the subclass attr and the BASE class method — a porter must replicate both directions or double-wrapping occurs; methods matching any accepted form are left untouched.
**Probe:** `grep -Fc 'remove_ctx' src/flask/app.py` ≥ 3 (def + two setattr sites incl. import in wrapper); `grep -Fc 'rpartition(".")[2] == "AppContext"' src/flask/app.py` = 1; test `tests/test_subclassing.py` pins the single documented subclass scenario.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "__init_subclass__ remove_ctx add_ctx override", limit: 6 });
```

## Verdict
Adopt dual-direction wrapping for API migrations. Adapt warning text. Omit once Flask 4 removes the shim.
