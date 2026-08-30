<!-- capsule-v2 -->
# Error-handler lookup — what key normalizes a registration and in what order do scopes/codes/classes win?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** Given `@app.errorhandler(x)`, what is stored, and given an exception, which handler is found first?

## _get_exc_class_and_code + _find_error_handler ladder
**Path/Symbol:** `src/flask/sansio/scaffold.py:Scaffold._get_exc_class_and_code` (664–706), `.register_error_handler` (649–662); `src/flask/sansio/app.py:App._find_error_handler` (868–891).
**Signature:** `_get_exc_class_and_code(code_or_exception: type[Exception]|int) -> tuple[type[Exception], int|None]`; `_find_error_handler(e, blueprints: list[str]) -> handler|None`.
**Data Shape:** registry `error_handler_spec[scope][code][exc_class] = fn` with `defaultdict(lambda: defaultdict(dict))`; scope None = app-wide.

### Decisive source
```python
if isinstance(exc_class_or_code, int):
    exc_class = default_exceptions[exc_class_or_code]   # KeyError → ValueError
...
if isinstance(exc_class, Exception):        # INSTANCE, not class
    raise TypeError(...)
if issubclass(exc_class, HTTPException):
    return exc_class, exc_class.code        # code from the CLASS, not the arg
else:
    return exc_class, None

# lookup:
for c in (code, None) if code is not None else (None,):
    for name in (*blueprints, None):        # innermost bp → ... → app
        for cls in exc_class.__mro__:       # exact class → base classes
            if (handler := self.error_handler_spec[name][c].get(cls)):
                return handler
```

**Flow:** registration validates int-against-werkzeug table, rejects instances and non-Exception classes, derives `(class, code)`; lookup iterates code-specific-then-generic × blueprint-innermost-to-app × MRO, returning the FIRST hit.
**Invariant:** blueprint handlers registered via `app.errorhandler` under scope name; a 404 handler for a blueprint only fires when the request's blueprint chain contains it — routing failures before match still consult the app scope. Registering for an instance (`errorhandler(ValueError())`) is always a TypeError even if werkzeug knows the code.
**Probe:** `grep -Fc 'return exc_class, exc_class.code' src/flask/sansio/scaffold.py` = 1; `grep -Fc 'is an instance, not a class.' src/flask/sansio/scaffold.py` = 1; tests `tests/test_user_error_handler.py::test_handle_class_or_code` (:253), `test_error_handler_subclass` (:61), `tests/test_blueprints.py::test_blueprint_specific_error_handling` (:7).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "errorhandler register error handler exc class code", limit: 8 });
```

## Verdict
Adopt the triple-loop precedence (code→generic, innermost→app, MRO) exactly — reordering changes which user handler runs. Adapt storage layout freely as long as lookup order matches. Omit nothing.
