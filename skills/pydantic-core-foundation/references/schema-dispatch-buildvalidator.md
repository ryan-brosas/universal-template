<!-- capsule-v2 -->
# Schema dispatch — how does a `{"type": ...}` dict become the right validator struct?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** What is the exact build/dispatch contract a port must reproduce so every schema type constructs identically (errors included)?

## One macro match over EXPECTED_TYPE consts; two entry points differ ONLY in prebuilt reuse
**Path/Symbol:** `src/validators/mod.rs:build_validator_inner/validator_match!/build_validator_base/build_validator` (:520-665).
**Signature:** `fn build_validator(schema: &Bound<'_, PyAny>, config: Option<&Bound<'_, PyDict>>, definitions: &mut DefinitionsBuilder<Arc<CombinedValidator>>) -> PyResult<Arc<CombinedValidator>>`.
**Data Shape:** Every validator module exports a type with `const EXPECTED_TYPE: &'static str` (e.g. `"union"`, `"model-fields"`, `"tagged-union"`) implementing `BuildValidator::build(schema_dict, config, definitions) -> PyResult<Arc<CombinedValidator>>` (:497-507). ~60 variants enumerated in `enum CombinedValidator` (:745-844) with `#[enum_dispatch]` forwarding `Validator::validate/default_value/validate_assignment/get_name`.

### Decisive source
```rust
macro_rules! validator_match {
    ($type:ident, $dict:ident, $config:ident, $definitions:ident, $($validator:path,)+) => {
        match $type {
            $(<$validator>::EXPECTED_TYPE => build_specific_validator::<$validator>($type, $dict, $config, $definitions),)+
            "invalid" => return py_schema_err!("Cannot construct schema with `InvalidSchema` member."),
            _ => return py_schema_err!(r#"Unknown schema type: "{}""#, $type),
        }
    };
}
```

**Flow:** `build_validator_base` (top-level, `use_prebuilt=false`) vs `build_validator` (nested, `use_prebuilt=true`): nested builds FIRST check `PrebuiltValidator::try_get_from_schema(type_, dict)` (:562-567) so an existing `SchemaValidator` on the same sub-schema is reused by reference instead of rebuilt (memory optimization; also the unpickling guard comment on :533). Type dispatch is plain string match on `schema["type"]`; missing required keys surface as `KeyError` wrapped into `SchemaError: Error building "<type>" validator:\n {...}` by `build_specific_validator` (:510-518).
**Invariant:** Build-time errors are ALWAYS `SchemaError` (a TypeError subclass) with the `Error building "{type}" validator:` prefix — never ValidationError (that is validation-time only). Unknown types fail loudly rather than defaulting.
**Probe:** `PYTHONPATH=python python -c "from pydantic_core import SchemaValidator; SchemaValidator({'type':'model-fields','fields':{'a':{'type':'int'}}})" ` → SchemaError mentioning `Error building "model-fields"` and `KeyError: 'schema'` (executed live this pass); `grep -c 'EXPECTED_TYPE' src/validators/*.rs | awk -F: '{s+=$2} END{print s}'` ≈ 60.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "build_validator validator_match Unknown schema type", limit: 5 });
// live rank-1: src.validators.mod.build_validator_inner line-exact (:551)
```

## Verdict
Adopt: single choke-point dispatcher, const-string registry, prebuilt short-circuit for nested builds only, SchemaError-wrapped build failures. Adapt the macro to your language's table/map idiom. Omit nothing here — the two-entry-point split (base vs nested) is load-bearing for pickle/unpickle identity.
