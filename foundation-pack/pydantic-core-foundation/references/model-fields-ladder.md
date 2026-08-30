<!-- capsule-v2 -->
# Model-fields validation — how are fields resolved (alias/name), defaults applied, extras handled, and what is returned?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** What is the per-field decision ladder and the exact success triple?

## LookupKeyCollection.select(by_alias, by_name) → validate | default ladder; output = (dict, extra_dict_or_None, fields_set)
**Path/Symbol:** `src/validators/model_fields.rs:ModelFieldsValidator::{build, validate, validate_assignment}` (whole file, 496L); `LookupKeyCollection` in `src/lookup_key.rs`.
**Signature:** build-time: `extras_schema`/`extras_keys_schema` are ERRORS unless `extra_behavior=allow` (:63-72); runtime returns `(model_dict: PyDict, Option<PyDict>, fields_set: PySet).into_py_any()`.
**Data Shape:** Per field: `{name, lookup_key_collection, name_py, validator, frozen}`; `loc_by_alias` default true; `validate_by_alias` default true / `validate_by_name` default false (via state `_or` helpers).

### Decisive source
```rust
let lookup_key = field.lookup_key_collection.select(validate_by_alias, validate_by_name)?;
let op_key_value = match dict.get_item(lookup_key) { ... };
// present:
match field.validator.validate(py, value.borrow_input(), state) {
    Ok(value) => { model_dict.set_item(&field.name_py, value)?; fields_set_count += 1; ... }
    Err(ValError::Omit) => continue,
    Err(ValError::LineErrors(line_errors)) => errors.push(
        lookup_path.apply_error_loc(err, self.loc_by_alias, &field.name)), ...
}
// absent:
match field.validator.default_value(py, Some(field.name.as_str()), state) {
    Ok(Some(value)) => model_dict.set_item(&field.name_py, value)?,
    Ok(None) => errors.push(lookup_key.error(ErrorTypeDefaults::Missing, ...)),
    Err(ValError::Omit) => {}
    ...
}
```

**Flow:** Input coercion first: `input.validate_model_fields(strict, from_attributes)`; DictType errors are REWRITTEN to ModelType(model_name) (:140-160) so wrong-container errors speak model language. The whole loop runs under TWO nested scopes: `rebind_extra(data = Some(model_dict.clone()))` (so validator functions see accumulated data) and `scoped_set(has_field_error=false)`, plus per-field `rebind_extra(field_name=...)`. Extras pass iterates remaining keys via used_keys set (built only when extra_behavior != Ignore AND not attribute-mode): Forbid ⇒ ExtraForbidden; Allow ⇒ optional extras-keys-validator validates the KEY, extras-validator the VALUE, results land in `__pydantic_extra__` dict which is created EVEN WHEN empty/from-attributes (:383-385). Success adds `state.add_fields_set(count)` feeding smart-union ranking. validate_assignment copies the data dict, DELETES the assigned key first ("V1 behaviour" — validators see data WITHOUT the new value), honors frozen with FrozenField, and splits extra-vs-known assignment by extra_behavior.
**Invariant:** Output keys are ALWAYS canonical field names (never aliases); fields_set tracks names actually validated-from-input plus allowed extras; missing+no-default ⇒ Missing keyed through the SAME lookup that found nothing (so alias configs produce correctly-located errors).
**Probe:** `grep -c 'fn validate_assignment' src/validators/model_fields.rs` =1; `grep -n 'V1 behaviour' src/validators/model_fields.rs` =1 (:419); direct tests: tests/validators/test_model_fields.py green this pass (551-passed batch incl test_errors+test_json).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "ModelFieldsValidator extras_schema used_keys", limit: 5 });
// live rank-family: ModelFieldsValidator.validate resolves line-exact in src/validators/model_fields.rs
```

## Verdict
Adopt: alias-or-name selection ladder, present→validate / absent→default dichotomy, Omit-swallowing field loop, always-canonical output names, delete-before-validate assignment semantics, extras keys+values both validatable. Adapt the triple shape to your model protocol (pydantic consumes it positionally). Omit nothing else — this file IS the model contract.
