<!-- capsule-v2 -->
# GeneralFieldsSerializer — how are model fields serialized, ordered, filtered, and strict-checked?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** What order do output keys take, when is a field skipped vs excluded, and what triggers UnexpectedValue in strict mode?

## INPUT-dict iteration order wins (not schema order); None-serializer means exclude; missing required fields fail strict checks
**Path/Symbol:** `src/serializers/fields.rs:GeneralFieldsSerializer::{new, main_to_python, main_serde_serialize, prepare_value}` (:121-321+); SerField :28-80.
**Signature:** `SerField { key_py, alias, alias_py, serializer: Option<Arc<CombinedSerializer>>, required, serialize_by_alias, serialization_exclude_if }`; FieldsMode `{SimpleDict, ModelExtra, TypedDictAllow}`.
**Data Shape:** `fields: AHashMap<String, SerField>` + precomputed `required_fields: usize`; missing-sentinel object skips unset-without-default entries.

### Decisive source
```rust
// NOTE! we maintain the order of the input dict assuming that's right
for result in main_iter {
    let (key, value) = result?;
    ...
    if let Some(field) = op_field {
        let serializer = Self::prepare_value(&value, field, &state.extra)?; // None => skip
        if field.required { used_req_fields += 1; }
        let Some(serializer) = serializer else { continue };
        (field.get_key_py(...), serializer)   // alias or name by extra.serialize_by_alias_or
    }
...
if state.check.enabled() && !(extra.exclude_defaults || extra.exclude_unset || extra.exclude_none
        || extra.exclude_computed_fields || state.exclude().is_some())
        && self.required_fields > used_req_fields {
    Err(PydanticSerializationUnexpectedValue::new(
        Some(format!("Expected {required_fields} fields but got {used_req_fields}")), ...))
```

**Flow:** Iteration follows the VALUE's dict/model-`__dict__`; each key resolves its SerField (unknown keys ⇒ TypedDictAllow extras / strict-check error / silent skip). Skips: exclude_none, missing sentinel, schema-level `serializer=None`, exclude_if callable returning true, exclude_defaults equality probe against serializer.get_default. Filters (include/exclude trees) consulted via `filter.key_filter` under scoped_include_exclude so nested structures inherit narrowed filters. serde path mirrors this but SKIPS the required-count check deliberately ("unions use to_python mode='json'" :301). prepare_value implements serialize_as_any: swaps the typed serializer for AnySerializer when the value's type isn't an exact match (duck-typing escape hatch).
**Invariant:** Output NEVER reorders relative to input. Strict check counts only when NO exclusion flags/filters are active — exclusions make counting impossible, so strictness yields instead of false-failing.
**Probe:** `grep -n 'None serializer means exclude' src/serializers/fields.rs` =1 (:32); `grep -cn 'NOTE!' src/serializers/fields.rs` =2; direct tests: tests/serializers/test_model.py green this pass (166 batch).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "GeneralFieldsSerializer main_to_python required_fields", limit: 5 });
// live rank-family: fields.rs symbols resolve line-exact
```

## Verdict
Adopt: input-order preservation, five distinct skip reasons in priority order, alias application at emit-time only, strict required-count gated on exclusion absence. Adapt AHashMap to any map — lookup order doesn't matter BECAUSE iteration is over input. Omit the FIXME asymmetry in TypedDictAllow serde path unless you port serde too.
