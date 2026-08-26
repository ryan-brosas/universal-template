<!-- capsule-v2 -->
# `"json"` schema type — what does the json validator consume, given input kind is relative?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** Why does `SchemaValidator(json_schema()).validate_json('{"a": 1}')` FAIL while `validate_python('{"a": 1}')` succeeds — and what must a port do about it?

## The json validator consumes JSON *text relative to its current input kind*
**Path/Symbol:** `src/validators/json.rs:JsonValidator` (:17-90; validate :52-85); build gates prebuilt-style Any-collapse (:31-45).
**Signature:** build: `EXPECTED_TYPE = "json"`, name becomes `json[<inner-name>]` or `json[any]`; validate: `fn validate(&self, py, input: &(impl Input<'py> + ?Sized), state) -> ValResult<Py<PyAny>>`.
**Data Shape:** inner `Option<Arc<CombinedValidator>>` is None when inner built to CombinedValidator::Any (repr shows `validator:None`, test_any_schema_no_schema :172-178).

### Decisive source
```rust
let v_match = validate_json_bytes(input)?;          // expects TEXT again
...
Some(ref validator) => {
    let json_value = JsonValue::parse_with_config(json_bytes, true, state.allow_partial)
        .map_err(|e| map_json_err(input, e, json_bytes))?;
    let mut json_state = state.rebind_extra(|e| { e.input_type = InputType::Json; });
    validator.validate(py, &json_value, &mut json_state)
}
None => { /* PythonParse { allow_inf_nan: true, cache_mode: state.cache_str(),
          partial_mode: state.allow_partial, catch_duplicate_keys: false } -> obj */ }
```

**Flow:** Python mode: str/bytes input → coerce → parse → validate inner under rebound Json input-type. JSON mode (inside validate_json): the funnel ALREADY parsed once, so a top-level `"json"` schema receives a parsed JsonValue and `validate_json_bytes` rejects it — mapped error reads `JSON input should be string, bytes or bytearray [type=json_type, input_value={'a': 1}, input_type=dict]`. Upstream's test_any only passes its json arm because conftest re-dumps inputs (`json.dumps(py_input)`), i.e. json-of-json needs doubly-encoded text. Probe-verified live (P4a-c).
**Invariant:** `"json"` always means "parse one more layer of text from here"; it never means "accept already-parsed data". Any-inner returns the raw parsed object with inf/nan allowed and duplicate keys preserved (catch_duplicate_keys:false). Build failure keeps SchemaError contract via EXPECTED_TYPE dispatch.
**Probe:** executed live this pass: P4a `validate_json(json.dumps('{"a": 1}')) == {'a': 1}`; P4c `validate_json(json.dumps(44))` → json_type with `input_value=44, input_type=int`; P5 `validate_python('{"a": 1}') == {'a': 1}`. Direct tests: `tests/validators/test_json.py:11-46` (test_any), `:49-94` (text over validate_python incl. lone-surrogate string_unicode), `:133-152` (dict-key use).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "JsonValidator EXPECTED_TYPE json parse_with_config rebind_extra", limit: 5 });
// live top-5: ValidationState.rebind_extra (:57) then JsonValidator.build (:26) / .validate (:53) / .get_name (:87) — json.rs block line-exact
```

## Verdict
Adopt the relative-text semantics and the Any-collapse fast path; adapt the jiter PythonParse knobs to your parser; document loudly that top-level json schemas need double encoding under validate_json. Coverage: all cited paths no_recorded_issue @ gen 2026-08-25T20:09:30Z.
