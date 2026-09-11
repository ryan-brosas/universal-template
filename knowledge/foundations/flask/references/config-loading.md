<!-- capsule-v2 -->
# Config loading — what does from_object/from_pyfile/from_prefixed_env actually accept, and how do nested env keys work?

**Source:** Flask BSD-3 `main@d318b683471101618febed18996405ad26462110`; Codebase Memory `ext-flask`. **Question:** What are the load rules and precedence a config port must reproduce?

## Config loaders + ConfigAttribute descriptor
**Path/Symbol:** `src/flask/config.py:Config` (50–367), `.from_prefixed_env` (126–185), `.from_object` (218–254), `.from_file` (256–302), `.get_namespace` (323–364); `ConfigAttribute` (20–47).
**Signature:** `from_prefixed_env(prefix="FLASK", *, loads=json.loads)`; `from_object(obj|import_name)`; `ConfigAttribute(name, get_converter=None)` descriptor.
**Data Shape:** dict subclass with `root_path`; values JSON-parsed when parseable, else raw string; nested keys split on `__`.

### Decisive source
```python
for key in sorted(os.environ):
    if not key.startswith(prefix): continue
    ...
    try: value = loads(value)
    except Exception: pass              # Keep the value as a string if loading failed.
    if "__" not in key:
        self[key] = value
        continue
    current = self
    *parts, tail = key.split("__")
    for part in parts:
        if part not in current:
            current[part] = {}          # intermediate dicts auto-created
        current = current[part]
    current[tail] = value
```
`from_object`: `for key in dir(obj): if key.isupper(): self[key] = getattr(obj, key)` — uppercase-only, works on modules AND classes. `Config.__setattr__`-style attribute access comes from `ConfigAttribute` descriptors on the app (`testing`, `secret_key`, `permanent_session_lifetime` w/ `_make_timedelta` converter).

**Flow:** sorted env iteration (deterministic) → strip prefix → best-effort JSON → flat or `__`-nested write. from_pyfile execs the file into a fresh module namespace then delegates to from_object; from_envvar wraps it with a missing-var RuntimeError (silent flag honored); silent file loads swallow only ENOENT/EISDIR/ENOTDIR.
**Invariant:** lowercase keys in a pyfile/object are IGNORED (private temporaries); env vars never overwrite pre-set non-env keys here (that's dotenv's rule, opposite direction); `FLASK_EXIST__inner__ik=2` mutates the existing nested dict rather than replacing `EXIST`.
**Probe:** `grep -Fc '*parts, tail = key.split("__")' src/flask/config.py` = 1; `grep -Fc '# Keep the value as a string if loading failed.' src/flask/config.py` = 1; `grep -Fc 'if key.isupper():' src/flask/config.py` = 2 (from_object + from_mapping); tests `tests/test_config.py::test_from_prefixed_env_nested` (:79), `::test_from_object` family.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-flask", query: "from_prefixed_env config environment nested", limit: 6 });
```

## Verdict
Adopt uppercase-filter + JSON-best-effort + `__` nesting. Adapt prefix/loads defaults per host. Omit get_namespace only if you lack namespace-style consumers.
