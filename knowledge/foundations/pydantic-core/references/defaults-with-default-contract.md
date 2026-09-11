<!-- capsule-v2 -->
# Defaults — when is a default copied, validated, or replaced by an error, and how does on_error work?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** What are the exact rules for `default`, `default_factory`, `validate_default`, `copy_default` and `on_error={raise,omit,default}`?

## Unhashable stored default ⇒ deepcopy per use; factories taking data are REFUSED after a field error
**Path/Symbol:** `src/validators/with_default.rs:WithDefaultValidator/DefaultType/OnError` (whole file, 236L).
**Signature:** `DefaultType::{None, Default(Py), DefaultFactory(Py, takes_data: bool)}`; build rejects `default`+`default_factory` together (:40) and `on_error='default'` without any default (:118-122).
**Data Shape:** `copy_default` is computed at BUILD time as `default_obj.bind(py).hash().is_err()` (:131-135) — hashability is the proxy for "safe to share".

### Decisive source
```rust
let copy_default = if let DefaultType::Default(default_obj) = &default {
    default_obj.bind(py).hash().is_err()   // unhashable => mutable => copy
} else { false };
...
if matches!(self.default, DefaultType::DefaultFactory(_, true)) && state.has_field_error {
    // The default factory might use data from fields that failed to validate
    let mut err = ValError::new(ErrorTypeDefaults::DefaultFactoryNotCalled, ...);
```

**Flow:** Input equal to `PydanticUndefined` sentinel ⇒ return default directly (:161-162). Sub-validation error ladder: UseDefault error (from `PydanticUseDefault` raised inside) ⇒ default regardless of on_error; other errors ⇒ on_error: Raise re-raises / Default substitutes / Omit converts to `ValError::Omit` which the FIELD LOOP swallows (field simply absent from output + fields_set). `default_value()` path: factory called with `{}` when takes_data but no accumulated data exists yet; stored defaults deepcopied iff copy_default; then `validate_default=true` runs the value through SELF.validate recursively (:204-214) with outer_loc attached to failures.
**Invariant:** The same WithDefaultValidator serves three call sites — field-absent (`default_value` via model-fields :230), get_default_value() top-level API, and error substitution — all through ONE `default_value(py, outer_loc, state)` so validation/copy semantics cannot diverge. Omit is the ONLY mechanism making a field vanish from both dict and fields_set.
**Probe:** `grep -n 'hash().is_err()' src/validators/with_default.rs` =1 (:132); direct tests: tests/validators/test_with_default.py::test_on_error_default :214, omit families at :46/:86/:99 — green this pass (in 283 batch).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "WithDefaultValidator on_error default_value", limit: 4 });
// live rank-family: with_default.rs symbols resolve line-exact
```

## Verdict
Adopt: hash-probe copy decision made once at build, single default_value funnel, on_error ladder ordering (UseDefault beats on_error), has_field_error gate for data-dependent factories. Adapt deepcopy to your host's copy protocol. Omit nothing — the build-time rejection pairs (default+factory; on_error=default w/o default) are user-facing contract.
