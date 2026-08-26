<!-- capsule-v2 -->
# self_instance / validate_init — how does validation populate a CALLER-CONSTRUCTED model instance instead of building one?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** How must `BaseModel.__init__`-style construction reuse an already-allocated instance, and how is that override kept from leaking into nested validators?

## Intercept at the model/dataclass boundary, immediately rebind `self_instance=None` for the subtree, then setattr fields onto the caller's object
**Path/Symbol:** entrypoints accept `self_instance` (`src/validators/mod.rs:171-198`, :207-233, :247-255) → `Extra.self_instance` (:687-735) → intercepts at `src/validators/model.rs:124-127` and `src/validators/dataclass.rs:538-540`; executor `ModelValidator::validate_init` (`model.rs:249-279`), dataclass twin (:632-647).
**Signature:** `fn validate_init(&self, py, self_instance: &Bound<PyAny>, input: &(impl Input + ?Sized), state: &mut ValidationState) -> ValResult<Py<PyAny>>`.
**Data Shape:** `self_instance: Option<&Bound<PyAny>>` on all three public entrypoints (python/isinstance/validate_json); threaded verbatim into per-call Extra; never stored on the validator.

### Decisive source
```rust
if let Some(self_instance) = state.extra().self_instance {
    // in the case that self_instance is Some, we're calling validation from within `BaseModel.__init__`
    return self.validate_init(py, self_instance, input, state);
}
...
fn validate_init<'py>(...) {
    // we need to set `self_instance` to None for nested validators as we don't want to operate on self_instance
    // anymore
    let state = &mut state.rebind_extra(|extra| extra.self_instance = None);
```

**Flow:** (1) caller passes `validate_python(data, self_instance=m2)`; (2) ModelValidator.validate sees Some and delegates BEFORE any instance/dict dispatch; (3) validate_init scopes `rebind_extra(self_instance=None)` so nested/inner validators allocate their own outputs; (4) inner validation runs; (5) root models: empty fields_set when input was undefined else `{__root__}`, then `force_setattr(__pydantic_fields_set__, …)` + `force_setattr(__root__, output)`; normal models: extract `(model_dict, model_extra, fields_set)` from the output triple and `set_model_attrs(self_instance, …)`; (6) `call_post_init(py, self_instance.clone(), input, state.extra())` runs hooks against the populated instance. The RETURN VALUE is still a freshly-shaped model object — tests pin that even with `self_instance` the validator "returns a model" (tests/validators/test_model_init.py:123 comment), and `ans == m2` identity (:38-42).
**Invariant:** the self_instance override lasts EXACTLY one validator level. A port that forgets the rebind makes every nested model write into the same foreign object (silent data corruption); one that skips force_setattr breaks `__pydantic_fields_set__` bookkeeping that serializers/revalidation rely on.
**Probe:** direct probe Q4 executed live @ pin mirroring test_model_init.py::test_model_init_nested (:45-85): build nested model schema, `m2 = MyModel()`, `v.validate_python({'field_a':'test','field_b':{'x_a':'foo','x_b':12}}, self_instance=m2)` → m2.field_a=='test', isinstance(m2.field_b, MyModel) with its OWN values, `m2.__pydantic_fields_set__ == {'field_a','field_b'}`. Root-model probe Q4b byte-matches test_model_root.py:196-201 shape: `validate_python('foobar', self_instance='foobar') == 'foobar'` (non-model self_instance passes through for root schemas).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "self_instance validate force polling recursive model", limit: 10 });
// live run this pass: rank-1 force_setattr (model.rs:379-392), ModelValidator.validate :118-182 and validate_init cluster nearby; dataclass twin visible via input_as_python_instance hits in dataclass.rs:538-555
```

## Verdict
Adopt single-level interception + immediate scoped clearing + post-population hook ordering; adapt `force_setattr` to your attribute protocol (bypass frozen/slots guards like upstream does); omit JSON-mode parity concerns — the same funnel serves validate_json with self_instance. Coverage: model.rs, mod.rs, dataclass.rs, test_model_init.py, test_model_root.py all no_recorded_issue @ gen 2026-08-25T20:09:30Z.
