<!-- capsule-v2 -->
# Static file route — why a weakref, and how do app vs blueprint static routes differ?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** How is the static endpoint registered on app and blueprint, and what lifetime trap does it avoid?

## weakref static view + blueprint static precedence
**Path/Symbol:** `src/flask/app.py:Flask.__init__` (347–364); `src/flask/sansio/blueprints.py:Blueprint.register` static block (323–328); `send_static_file`/`get_send_file_max_age` twins (app.py:366–413; blueprints.py:55–102); refcount test rationale test_basic.py:1959–1975 (#3761).
**Signature:** rule `f"{static_url_path}/<path:filename>"`, endpoint `"static"`, host=static_host; view = `lambda **kw: self_ref().send_static_file(**kw)`.
**Data Shape:** app static defaults ON (`static_folder="static"`); blueprint static OFF unless passed; blueprint static route registered at REPLAY time via state.add_url_rule → endpoint `<bpname>.static`.

### Decisive source
```python
# Use a weakref to avoid creating a reference cycle between the app
# and the view function (see #3761).
self_ref = weakref.ref(self)
self.add_url_rule(
    f"{self.static_url_path}/<path:filename>",
    endpoint="static",
    host=static_host,
    view_func=lambda **kw: self_ref().send_static_file(**kw),
)
```
Blueprint twin resolves max_age against the CURRENT APP config (`current_app.config["SEND_FILE_MAX_AGE_DEFAULT"]`) but serves the BLUEPRINT's folder; None max_age ⇒ conditional requests instead of timed cache.

**Flow:** init asserts `bool(static_host) == host_matching`; registration without checking folder existence (may appear at runtime); request → send_from_directory(safe_join) with per-app/per-bp max_age.
**Invariant:** without the weakref the lambda pins the app through its own view_functions dict and CPython never collects it — any port that stores bound methods in a global registry has this bug; blueprint static requires url_prefix to be reachable (else app static shadows).
**Probe:** `grep -Fc 'weakref.ref(self)' src/flask/app.py` = 1; test `tests/test_basic.py::test_app_freed_on_zero_refcount` (:1960, require_cpython_gc) pins collection; `tests/test_blueprints.py::test_default_static_max_age` (:221).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "send_static_file weakref static route", limit: 6 });
```

## Verdict
Adopt weakref-view pattern for any self-referential registration. Adapt path rules. Omit GAE commentary.
