<!-- capsule-v2 -->
# compile_path + convertor registry — how do `{param:type}` path templates become regexes and back?

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** What exact grammar turns a path template into a matcher, and which round-trip guarantees does URL reversal depend on?

## PARAM_REGEX / compile_path
**Path/Symbol:** `starlette/routing.py:PARAM_REGEX` (:108), `starlette/routing.py:compile_path` (:111-164).
**Signature:** `compile_path(path: str) -> tuple[Pattern[str], str, dict[str, Convertor[Any]]]`.
**Data Shape:** input `"/users/{id:int}"` → (compiled `^(...)$` regex with named groups, canonical `path_format` `"/users/{id}"`, `{param: convertor}` map). `is_host = not path.startswith("/")` switches to host-mode (port stripped before anchoring).

### Decisive source
```python
PARAM_REGEX = re.compile("{([a-zA-Z_][a-zA-Z0-9_]*)(:[a-zA-Z_][a-zA-Z0-9_]*)?}")
...
param_name, convertor_type = match.groups("str")   # missing type DEFAULTS to "str"
convertor_type = convertor_type.lstrip(":")
assert convertor_type in CONVERTOR_TYPES, ...
path_regex += re.escape(path[idx : match.start()])
path_regex += f"(?P<{param_name}>{convertor.regex})"
```

**Flow:** literal segments are `re.escape`d; each param becomes a named group over the convertor's regex; duplicate param names raise `ValueError`; the pattern is anchored `^...$`. `path_format` keeps `{name}` placeholders for later `replace_params` reversal.
**Invariant:** match-time `convert()` and reverse-time `to_string()` are two halves of ONE contract — `IntegerConvertor.to_string` asserts non-negative because its regex `[0-9]+` can't re-match `-3`; `StringConvertor` asserts no `/` and non-empty. Break either assert and `url_path_for` emits URLs that will never route back.
**Probe:** `tests/test_routing.py::test_route_converters` (:226) pins int/float/uuid/path matching; `::test_duplicated_param_names` (:754) pins the dup-param raise.

## Convertor registry + per-convertor regexes
**Path/Symbol:** `starlette/convertors.py:CONVERTOR_TYPES` (:79-85), `register_url_convertor` (:88-89).
**Data Shape:** module-level singleton dict keyed by suffix (`str`→`[^/]+`, `path`→`.*`, `int`→`[0-9]+`, `float`→`[0-9]+(\.[0-9]+)?`, `uuid`→hex-with-optional-dashes). Registration mutates the GLOBAL table — every router in the process sees it.
**Flow:** `FloatConvertor.to_string` renders `%0.20f` then strips trailing zeros/dot — deterministic textual form so reversal is stable. UUID regex accepts both dashed and undashed forms but always outputs dashed via `str(uuid)`.
**Invariant:** convertors are stateless singletons; a custom convertor MUST define both directions plus a ClassVar `regex` string, or `compile_path` raises at import time of the routes module.
**Probe:** `tests/test_convertors.py` (whole file pins all five convert() round trips).

## replace_params / url_path_for recursion
**Path/Symbol:** `starlette/routing.py:replace_params` (:93-104), `Route.url_path_for` (:260-269), `Mount.url_path_for` (:427-452).
**Data Shape:** pops each supplied param whose `{key}` appears in the format string, converting via `to_string`; leftover params mean "keep recursing" for mounts (`<mount_name>:<child_name>` name splitting) or an assert failure on plain routes.
**Flow:** Router.url_path_for tries each route in order, swallowing `NoMatchFound`; Mount strips its own prefix, substitutes `"path"` with the remainder, then delegates to child routes.
**Invariant:** `seen_params != expected_params` raises BEFORE any substitution — extra/missing kwargs are hard errors, not silently dropped.
**Probe:** `tests/test_routing.py::test_url_path_for` (:261) and `::test_reverse_mount_urls` (:386).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "compile_path", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "replace_params", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "url_path_for", limit: 20 });
```

## Verdict
Adopt the template grammar, default-to-str typing, anchored named groups, and the two-way convertor contract verbatim. Adapt the registry if you need per-router scoping instead of process-global mutation. Omit host-mode only if you have no Host routing (the same function serves both).
