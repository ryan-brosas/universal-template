<!-- capsule-v2 -->
# Model instance fast path — what happens when you validate an EXISTING model instance, and why does constructing a new one floor exactness to Strict?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** A porter must decide when validating a model instance returns it as-is vs revalidates, and how that choice feeds smart-union ranking.

## Exact instances reuse `__pydantic_fields_set__`; generic-origin instances force revalidation; construction floors exactness DOWN to Strict
**Path/Symbol:** `src/validators/model.rs:ModelValidator::validate` (:117-182), `Revalidate` (:28-51); helpers `downcast_python_input`/`input_as_python_instance` (`src/input/input_python.rs:65-74`).
**Signature:** `fn should_revalidate(&self, input: &Bound<PyAny>, class: &Bound<PyType>) -> bool` over `enum Revalidate { Always, Never, SubclassInstances }`.
**Data Shape:** `(py_instance_input: Option<&Bound<PyAny>>, force_revalidate: bool)` decided before any dict path; generic_origin is an Option<PyType> baked at build.

### Decisive source
```rust
// if the model has a generic origin, we allow input data to be instances of the generic origin rather than the class,
// as cases like isinstance(SomeModel[Int], SomeModel[Any]) fail the isinstance check, but are valid, we just have to enforce
// that the data is revalidated, hence we set force_revalidate to true
match input_as_python_instance(input, generic_origin) { Some(x) => (Some(x), true), ... }
...
} else {
    // Having to construct a new model is not an exact match
    state.floor_exactness(Exactness::Strict);
    self.validate_construct(py, input, None, state)
}
```

**Flow:** `input_as_python_instance(input, class)` = `as_python().filter(is_instance.unwrap_or(false))` — is_instance errors count as false. Exact instance → read `__pydantic_fields_set__`, revalidate from `__dict__` (merging `__pydantic_extra__` into a copied dict when present :162-171) unless `should_revalidate` says return as-is (`Ok(input.to_object(py)?)` :174-176). SubclassInstances mode ⇒ revalidate exactly when NOT `is_exact_instance`. Generic-origin match → same construct path with fields_set preserved but forced. NO instance match → `floor_exactness(Strict)` then validate_construct; since `floor_exactness` records the LOWER of current vs given (validation_state.rs:110-125 "Sets the exactness to the lower… used in union validation"), construction can never rank as Exact in smart-union scoring — only an already-built instance can.
**Invariant:** revalidate policy gates REUSE of the input object identity; exactness flooring gates UNION RANKING — two independent axes. Caller resolution note (closes the pass-1 graph caveat): the graph shows callers_total=0 for monomorphized `downcast_python_input` because CALLS edges don't record generic instantiations; direct grep finds its 4 call sites ALL in validators/url.rs (:207,:215,:459,:462 PyUrl/PyMultiHostUrl fast paths), while `input_as_python_instance` is called from model.rs:137/:144, dataclass.rs:548/:555, uuid.rs:107.
**Probe:** direct probe Q5 executed live @ pin mirroring tests/validators/test_model.py::test_revalidate_always/:703-754 shape: default (`revalidate_instances='never'`) validating an existing MyModel returns the SAME object unchanged; `'always'` rebuilds via __dict__; subclass input under default policy passes through. Exactness probe Q5b: smart-union of model|str prefers the str arm for raw dicts (construction not Exact) while an existing instance wins the model arm.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "should_revalidate revalidate mode enum", limit: 10 });
// live run this pass: Revalidate.should_revalidate model.rs:44-50 rank-1; test_revalidate* functions cluster behind it; floor_exactness surfaces under validation_state queries (see self-instance + validation-state capsules for its other consumers)
```

## Verdict
Adopt the three-mode revalidate enum plus generic-origin force flag verbatim; adapt identity-return to your host's ownership rules (returning a borrowed instance is safe here because validators are immutable); do NOT let construction rank above Exact-instance matches in union scoring — the floor call is load-bearing for smart-union parity. Coverage: model.rs, input_python.rs, validation_state.rs no_recorded_issue @ gen 2026-08-25T20:09:30Z; graph-caller caveat resolved by direct grep this pass.
