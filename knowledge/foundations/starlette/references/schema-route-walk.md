<!-- capsule-v2 -->
# SchemaGenerator route walk + docstring-YAML contract

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** How does the OpenAPI generator traverse mounts/hosts and turn endpoint docstrings into schema entries?

## BaseSchemaGenerator.get_endpoints
**Path/Symbol:** `starlette/schemas.py:get_endpoints` (:40-87) + `_remove_converter` (:89-96).
**Data Shape:** recursive walk producing `EndpointInfo(path, http_method, func)` NamedTuples; Mount contributes its converter-stripped prefix, Host contributes "" (host-level paths unversioned); `include_in_schema=False` routes skipped; class endpoints enumerated by probing the fixed 6-verb method table; HEAD suppressed.
### Decisive source
```python
_remove_converter_pattern = re.compile(r":\w+}")
def _remove_converter(self, path): return _remove_converter_pattern.sub("}", path)
# "/users/{id:int}" → "/users/{id}"
```
**Flow:** NOTE the recursion quirk: `routes = route.routes or []` REBINDS the loop variable — harmless here because sub_endpoints are computed immediately, but a porter turning this into a generator must fix the rebinding first.
**Probe:** `tests/test_schemas.py::test_schema_generation` (:133) pins the full walk incl. mounted routes.

## parse_docstring + SchemaGenerator.get_schema
**Path/Symbol:** `starlette/schemas.py:parse_docstring` (:98-120), `get_schema` (:132-148).
**Data Shape:** docstring split on `---`, LAST segment YAML-loaded; non-dict results ignored (plain prose docstrings safe); entries merged under `schema["paths"][path][method]`; base_schema deep-copied shallowly (dict(self.base_schema)).
**Invariant:** missing pyyaml degrades to assertion errors at USE time, not import time (module import stays cheap).
**Probe:** `::test_schema_endpoint` (:250).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "get_endpoints", limit: 5 });
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "parse_docstring", limit: 5 });
```

## Verdict
Adopt the walk pattern for any route-introspection tool. Adapt to your doc convention (this one is yaml-after----). Omit if you generate schemas from type info instead of prose.
