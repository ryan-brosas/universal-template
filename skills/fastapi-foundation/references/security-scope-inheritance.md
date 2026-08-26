<!-- capsule-v2 -->
# Security scope inheritance + OpenAPI extraction — How do Security scopes accumulate down the dependency tree and surface in the schema?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** How are a dependency's required scopes computed from parents + own declarations, and how does the same walk feed `security` requirements into OpenAPI?

## Scope accumulation at build time; reuse at schema time
**Path/Symbol:** `fastapi/dependencies/utils.py:get_dependant` (271–347: `current_scopes = parent + own`, passed to children at 318–330) + `_get_oauth_scopes` (`dependencies/models.py:71–79`) + OpenAPI twin `fastapi/openapi/utils.py:_get_openapi_dependency_data` (99–129) + `_get_openapi_security_definitions` (132–156).
**Signature:** `_get_oauth_scopes(*, dependant) -> list[str]` (parents first, own appended order-preserving, deduped by membership scan); `_get_openapi_dependency_data(dependant) -> _OpenAPIDependencyData`.
**Data Shape:** runtime injection: `SecurityScopes(scopes=_get_oauth_scopes(dependant))` delivered to params named `security_scopes` (solve_dependencies 721–724); schema side collects `(dependant, oauth_scopes)` pairs for non-root security schemes.

### Decisive source
```python
        if not is_root and _is_security_scheme(dependant=current_dependant):
            dependency_data.security_dependencies.append((current_dependant, oauth_scopes))
        ...
        dependants.extend(
            (sub_dependant, oauth_scopes, False)
            for sub_dependant in reversed(current_dependant.dependencies))
```
and merging for the operation:
```python
    operation_security_dict: dict[str, list[str]] = {}
    for security_dependency, oauth_scopes in security_dependencies:
        ...
        for scope in oauth_scopes:
            if scope not in operation_security_dict[security_name]:
                operation_security_dict[security_name].append(scope)
    operation_security = [{name: scopes} for name, scopes in operation_security_dict.items()]
```

**Flow:** child Dependants receive `parent_oauth_scopes=current_scopes` at BUILD time so every node knows its cumulative requirement → at request time the solver hands each level's union to `SecurityScopes`-typed params so guards can enforce "has ALL inherited scopes" → the SAME cache-key-deduped walk in openapi/utils collects scheme+scopes pairs; multiple uses of one scheme merge their scope lists into a single requirement dict.
**Invariant:** (1) Scope lists preserve declaration ORDER (deliberately no set) — docs output and enforcement messages stay stable. (2) Root-level security deps don't produce operation `security` entries (is_root flag) — only nested ones do. (3) The visited-set is the DependencyCacheKey, so diamond-shaped dependency graphs emit each scheme once per unique (call, scopes, scope-mode).
**Probe:** `tests/test_security_scopes.py` enforces the injected `SecurityScopes` contract; `tests/test_ws_router.py:test_router_ws_depends_with_override` + openapi security snapshot tutorials pin the merged `{scheme: [scopes]}` shape.
