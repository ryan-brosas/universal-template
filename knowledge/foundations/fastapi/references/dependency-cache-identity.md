<!-- capsule-v2 -->
# Dependency cache key — When does the same callable count as "the same dependency"?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** What exactly is the cache identity of a solved dependency, and why can the same function solve twice with different scopes?

## Cache-key construction
**Path/Symbol:** `fastapi/dependencies/models.py:_get_cache_key` (lines 82–96) + `_uses_scopes` (99–120) + `_get_computed_scope` (229–235); type alias in `fastapi/types.py:DependencyCacheKey`.
**Signature:** `_get_cache_key(*, dependant: Dependant, uses_scopes_cache: _UsesScopesCache | None = None) -> tuple[Callable | None, tuple[str, ...], str]`.
**Data Shape:** `DependencyCacheKey = (dependant.call, scopes_for_cache, computed_scope_or_empty)` where `scopes_for_cache = tuple(sorted(set(own + inherited oauth scopes)))` ONLY when the dependency (transitively) uses scopes, else `()`.

### Decisive source
```python
def _get_cache_key(*, dependant, uses_scopes_cache=None) -> DependencyCacheKey:
    scopes_for_cache = (
        tuple(sorted(set(_get_oauth_scopes(dependant=dependant))))
        if _uses_scopes(dependant=dependant, cache=uses_scopes_cache)
        else ()
    )
    return (
        dependant.call,
        scopes_for_cache,
        _get_computed_scope(dependant=dependant) or "",
    )

def _get_computed_scope(*, dependant) -> str | None:
    if dependant.scope:
        return dependant.scope
    if _is_gen_callable(dependant.call) or _is_async_gen_callable(dependant.call):
        return "request"          # generator deps are implicitly request-scoped
    return None
```

**Flow:** `_uses_scopes` walks the sub-tree (memoized per-request in `_UsesScopesCache = dict[int, (Dependant, bool)]`, identity-checked via `cached[0] is dependant`) — true if own oauth scopes, a `SecurityScopes` param, an unwrapped `SecurityBase` class, or any transitive child uses scopes. Only then do scopes participate in the key.
**Invariant:** (1) Identity is `(callable object, effective-scope-set, computed scope)` — NOT parameter names; two path operations sharing a dependency share one call per request regardless of argument names. (2) The same callable used once bare and once with `Security(scopes=["x"])` yields TWO cache entries and TWO calls. (3) A plain callable's scope component is `""`; generators are forced to `"request"` because their teardown must survive until request end.
**Probe:** `tests/test_dependency_cache.py:test_security_cache` — one counter dependency declared both as `Depends(dep)` and `Security(dep, scopes=["scope"])`: bare form hits the cache (counter 1), each distinct scope set re-calls.
