<!-- capsule-v2 -->
# Dependency solver tree-walk — How are sub-dependencies solved, cached, and error-short-circuited at request time?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** When a path operation has nested `Depends()`, in what order are they called, when is the same dependency NOT called twice, and what happens to already-solved values when a sibling dependency fails validation?

## Recursive solve over the dependant tree
**Path/Symbol:** `fastapi/dependencies/utils.py:solve_dependencies` (lines 586–731), recursive call at 640–651.
**Signature:** `async def solve_dependencies(*, request, dependant, body=None, background_tasks=None, response=None, dependency_overrides_provider=None, dependency_cache=None, async_exit_stack, embed_body_fields, _uses_scopes_cache=None) -> SolvedDependency`.
**Data Shape:** `SolvedDependency` dataclass = `{values: dict[str, Any], errors: list, background_tasks: StarletteBackgroundTasks | None, response: Response, dependency_cache: dict[DependencyCacheKey, Any]}`. `values` keys are *parameter names* for sub-dependencies (`sub_dependant.name`) and field names for params.

### Decisive source
```python
        if (
            dependency_overrides_provider
            and dependency_overrides_provider.dependency_overrides
        ):
            original_call = sub_dependant.call
            call = getattr(
                dependency_overrides_provider, "dependency_overrides", {}
            ).get(original_call, original_call)
            ...
            use_sub_dependant = get_dependant(   # REBUILD the dependant from the override's signature
                path=use_path,
                call=call,
                name=sub_dependant.name,
                parent_oauth_scopes=_get_oauth_scopes(dependant=sub_dependant),
                scope=sub_dependant.scope,
            )

        solved_result = await solve_dependencies(...)   # recurse into sub-dependencies FIRST
        background_tasks = solved_result.background_tasks
        if solved_result.errors:
            errors.extend(solved_result.errors)
            continue                                    # do NOT call this dependency...
        sub_dependant_cache_key = _get_cache_key(dependant=sub_dependant, uses_scopes_cache=_uses_scopes_cache)
        if sub_dependant.use_cache and sub_dependant_cache_key in dependency_cache:
            solved = dependency_cache[sub_dependant_cache_key]   # ...reuse instead
```

**Flow:** depth-first over `dependant.dependencies` → per child: apply override (rebuilding the child Dependant so its own signature is analyzed fresh) → recurse → if child produced errors, extend parent `errors` and `continue` WITHOUT calling the child's callable and without caching → else cache-check `(call, scopes_tuple, computed_scope)` key → call via `_solve_generator` (yield-deps), `await call(**values)` (coroutine), or `run_in_threadpool` (sync) → store under the *parameter name* → then solve own path/query/header/cookie/body params and inject non-field params (`request`, `background_tasks`, `response`, `SecurityScopes`).
**Invariant:** (1) A dependency whose sub-dependency failed validation is NEVER invoked and never enters the cache — errors propagate up while siblings still run. (2) The cache lives on ONE `SolvedDependency.dependency_cache` dict threaded through every recursion level, so sharing is per-request, not global. (3) Overrides replace the callable BEFORE signature analysis, so an override with different params works.
**Probe:** `tests/test_dependency_cache.py` (`test_normal_counter`, `test_sub_counter`, `test_sub_counter_no_cache`, `test_security_cache`) — counter dependency increments once per request even when reached through two paths; `use_cache=False` forces a second call; same callable with different `Security(scopes=...)` counts as a DIFFERENT cache entry.
