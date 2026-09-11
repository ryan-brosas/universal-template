<!-- capsule-v2 -->
# JSON provider — how do jsonify semantics and compact/debug formatting live behind a swappable object?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What is the provider contract and what exactly does `app.json.response()` emit?

## JSONProvider / DefaultJSONProvider
**Path/Symbol:** `src/flask/json/provider.py:JSONProvider` (19–105), `.DefaultJSONProvider` (124–215); `_default` serializer hook (108–121).
**Signature:** `dumps(obj, **kwargs) -> str`; `loads(s, **kwargs)`; `response(*args, **kwargs) -> Response`; `_prepare_response_obj(args, kwargs)` (args XOR kwargs; neither ⇒ None; 1 positional ⇒ itself; else args-list or kwargs-dict).
**Data Shape:** provider holds `weakref.proxy(app)` as `_app` (no reference cycle); class attrs `default`, `ensure_ascii=True`, `sort_keys=True`, `compact=None`, `mimetype`.

### Decisive source
```python
if (self.compact is None and self._app.debug) or self.compact is False:
    dump_args.setdefault("indent", 2)
else:
    dump_args.setdefault("separators", (",", ":"))
return self._app.response_class(f"{self.dumps(obj, **dump_args)}\n", mimetype=self.mimetype)
```
`_default`: date→http_date; Decimal/UUID→str; dataclass→asdict; `__html__`→str; else TypeError.

**Flow:** make_response dict/list branch and `flask.jsonify` both funnel into provider.response → arg/kwargs exclusivity check → debug-aware indent vs separators → ALWAYS a trailing newline → response with application/json.
**Invariant:** the trailing `\n` is unconditional (test suites grep for it); `sort_keys` default True aids caching; swapping `app.json` swaps request.json parsing too (`request.json_module = app.json` set in `from_environ`).
**Probe:** `grep -Fc 'dump_args)}\n"' src/flask/json/provider.py` = 1 (needle `f"{self.dumps(obj, **dump_args)}\n"`); test `tests/test_json.py::test_jsonify_*` family pins output shape incl. newline.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "DefaultJSONProvider dumps loads response compact", limit: 6 });
```

## Verdict
Adopt the provider seam + weakref back-pointer + trailing-newline contract. Adapt `_default` type table. Omit the file-based load/dump wrappers if unused.
