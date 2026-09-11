<!-- capsule-v2 -->
# SchemaValidator surface — what do the entry methods guarantee, and how does the input abstraction stay zero-copy?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** Which public validate methods exist, how do their error/return contracts differ, and how do Python vs Json inputs share one code path?

## isinstance swallows LineErrors→False; JSON parses once then borrows; Input trait = strict/lax pair convention
**Path/Symbol:** `src/validators/mod.rs:SchemaValidator` (:108-495); `src/input/input_abstract.rs:Input trait` (:58-110+).
**Signature:** `validate_python/validate_json/validate_strings/validate_assignment/isinstance_python/get_default_value`; `_validate` builds `ValidationState::new(Extra::new(...), &mut RecursionState::default(), allow_partial)` fresh PER CALL (:419-450).
**Data Shape:** `Input<'py>` implemented by `&Bound PyAny` (python), jiter `JsonValue<'j>` (json), `StringMapping` (strings); every primitive conversion returns `ValMatch<T> = ValResult<ValidationMatch<T>>` where ValidationMatch tags Exact|Lax so unions can score.

### Decisive source
```rust
// isinstance: LineErrors mean "didn't validate", everything else is a REAL error:
match self._validate(...) {
    Ok(_) => Ok(true),
    Err(ValError::InternalErr(err)) => Err(err),
    Err(ValError::Omit) => Err(ValidationError::omit_error()),
    Err(ValError::UseDefault) => Err(ValidationError::use_default_error()),
    Err(ValError::LineErrors(_)) => Ok(false),
}
// validate_json: parse ONCE into jiter, then run the SAME _validate with borrowed slices
let json_value = jiter::JsonValue::parse_with_config(json_data, true, allow_partial)
    .map_err(|e| json::map_json_err(input, e, json_data))?;
```

**Flow:** All entries funnel through `_validate(input: &(impl Input + ?Sized), input_type, ...)` — the generic hides whether bytes were parsed or objects borrowed; per-call state means validators are Send+Sync-shareable and thread-safe by construction (no interior mutability except expected_json_size on the serializer). Convention (input_abstract :54-57): implement strict_*+lax_* when they differ, else validate_* delegating. allow_partial threads through `enumerate_last_partial` iterators so streaming/partial payloads can stop mid-collection.
**Invariant:** ValidationError construction is deferred to the boundary (`prepare_validation_err`) with title from config or top validator name; nothing inside the tree touches PyErr-raising for validation failures — only InternalErr carries real exceptions.
**Probe:** `grep -n 'fn _validate' src/validators/mod.rs` ≥2 (_validate+_validate_json); direct tests: test_union+test_model_fields+test_errors+test_json green this pass.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "SchemaValidator validate_python isinstance_python", limit: 4 });
// live rank-family: mod.rs methods resolve line-exact
```

## Verdict
Adopt: single generic funnel over an input abstraction, per-call fresh state, four-variant error mapping in boolean-check APIs, exactness-tagged primitive conversions. Adapt Input to your IR (enum of owned/borrowed). Omit validate_strings if you lack a string-mapping use case.
