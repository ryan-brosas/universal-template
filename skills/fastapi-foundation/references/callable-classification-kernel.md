<!-- capsule-v2 -->
# Callable classification kernel — How does FastAPI know a dependency is a generator, coroutine, or sync callable (through partials, functors, and classes)?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** How is `_is_coroutine_callable` decided for wrapped/functor callables without misclassifying classes as coroutines, and why the identity-keyed cache?

## Cached three-way classifier
**Path/Symbol:** `fastapi/dependencies/models.py:_is_gen_callable_cached` (137–158), `_is_async_gen_callable_cached` (167–188), `_is_coroutine_callable_cached` (197–220); helpers `_unwrapped_call`/`_impartial` (18–28); `_CallIdentity` (58–68).
**Signature:** `_is_gen_callable(call) / _is_async_gen_callable(call) / _is_coroutine_callable(call) -> bool`; cache `@lru_cache(maxsize=4096)` keyed on `_CallIdentity` (`__hash__ = id(call)`, `__eq__` identity).
**Data Shape:** classification ladder per predicate: partial-stripped object → unwrap-decorated function → class short-circuit False → functor `__call__` of both layers.

### Decisive source
```python
@lru_cache(maxsize=_CALLABLE_CLASSIFICATION_CACHE_SIZE)
def _is_coroutine_callable_cached(call_identity: _CallIdentity) -> bool:
    call = call_identity.call
    if inspect.isroutine(_impartial(call)) and iscoroutinefunction(_impartial(call)):
        return True
    if inspect.isroutine(_unwrapped_call(call)) and iscoroutinefunction(_unwrapped_call(call)):
        return True
    if inspect.isclass(_unwrapped_call(call)):
        return False                     # __init__ may be async-adjacent; class dep = sync ctor path
    dunder_call = getattr(_impartial(call), "__call__", None)
    if dunder_call is not None and iscoroutinefunction(_impartial(dunder_call)): return True
    ...
# 3.13+ uses inspect.iscoroutinefunction; <3.13 uses asyncio.iscoroutinefunction
```

**Flow:** every dispatch site in `solve_dependencies` / `get_request_handler` asks these predicates to choose between `_solve_generator` (enter CM on an exit stack), direct `await call(**values)`, or `run_in_threadpool`. `_get_computed_scope` also uses gen-predicates to force implicit `"request"` scope.
**Invariant:** (1) The lru_cache is keyed by callable IDENTITY — value-based hashing would collide across distinct closures; maxsize 4096 bounds memory while making repeated per-request classification free. (2) A class with async `__call__` still classifies via its instance `__call__`, but the CLASS itself short-circuits False so `Depends(MyClass)` runs the constructor in the threadpool. (3) Sync generators are lifted into the threadpool-aware `contextmanager_in_threadpool` so their bodies never block the loop.
**Probe:** `tests/test_dependency_class.py` + `tests/test_dependency_contextmanager.py` — class-callable deps and sync/async yield-deps exercise all three classifiers end-to-end.
