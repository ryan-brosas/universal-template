<!-- capsule-v2 -->
# Dependency scope rule — Why can a request-scoped generator dependency not depend on a function-scoped dependency?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** When exactly is `DependencyScopeError` raised and which direction of nesting is illegal?

## Build-time scope containment check
**Path/Symbol:** `fastapi/dependencies/utils.py:get_dependant` (302–317) + `fastapi/exceptions.py:DependencyScopeError` (167–171) + computed scope in `dependencies/models.py:_get_computed_scope` (229–235).
**Signature:** raise condition inside the signature walk: parent is gen/async-gen callable AND `_get_computed_scope(dependant) == "request"` AND `param_details.depends.scope == "function"`.
**Data Shape:** `Depends(scope: Literal["function", "request"] | None)`; None + generator callable ⇒ implicitly "request".

### Decisive source
```python
        if param_details.depends is not None:
            assert param_details.depends.dependency
            if (
                (
                    _is_gen_callable(dependant.call)
                    or _is_async_gen_callable(dependant.call)
                )
                and _get_computed_scope(dependant=dependant) == "request"
                and param_details.depends.scope == "function"
            ):
                call_name = getattr(dependant.call, "__name__", "<unnamed_callable>")
                raise DependencyScopeError(
                    f'The dependency "{call_name}" has a scope of '
                    '"request", it cannot depend on dependencies with scope "function".'
                )
```

**Flow:** scope is validated when the dependant TREE IS BUILT (route registration), not per request — a request-scoped generator's teardown runs after the response, but a function-scoped child's teardown already ran before send; letting it nest would make the parent's post-send code reference an already-closed resource → the error names the PARENT callable so the fix location is obvious.
**Invariant:** (1) Only the request→function direction is illegal; function-scoped parents may use request-scoped children. (2) The check uses `_get_computed_scope` (explicit scope first, then generator-implied "request"), so declaring `Depends(scope="function")` on a generator parent ALSO trips it via its explicit scope. (3) Because it fires at import/registration time, misconfigured apps never serve a single request.
**Probe:** `tests/test_dependency_scope.py` (if present at this pin) or the docs-backed scope tutorial tests pin both the raised type and message shape.
