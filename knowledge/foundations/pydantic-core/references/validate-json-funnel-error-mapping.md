<!-- capsule-v2 -->
# validate_json funnel — where do str/bytes/bytearray get coerced, and how do jiter parse errors become ValidationError locations?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** What is the exact acceptance ladder and error-shape contract for JSON-text entry points?

## Coerce → parse once → map JsonError onto the ORIGINAL input
**Path/Symbol:** `src/validators/mod.rs:SchemaValidator.validate_json` (:246-281) + `_validate_json` (:453-482); `src/validators/json.rs:validate_json_bytes` (:92-102), `map_bytes_error` (:104-111), `map_json_err` (:113-121).
**Signature:** `fn validate_json_bytes<'a,'py>(input: &'a (impl Input<'py> + ?Sized)) -> ValResult<ValidationMatch<EitherBytes<'a,'py>>>`; `fn map_json_err(input, error: jiter::JsonError, json_bytes: &[u8]) -> ValError`.
**Data Shape:** accepts str / bytes / bytearray (probe P1); anything else fails with `json_type`. Parse errors carry `ctx.error = e.description(json_bytes)` — jiter's message already includes `at line L column C`.

### Decisive source
```rust
pub fn map_json_err<'py>(input: &(impl Input<'py> + ?Sized), error: jiter::JsonError, json_bytes: &[u8]) -> ValError {
    ValError::new(
        ErrorType::JsonInvalid { error: error.description(json_bytes), context: None },
        input,
    )
}
```

**Flow:** `validate_json` → `json::validate_json_bytes(input)` (Python-mode bytes ladder; any BytesType line error is remapped to JsonType so the funnel reports "JSON input should be string, bytes or bytearray") → `_validate_json` parses ONCE via `jiter::JsonValue::parse_with_config(json_data, true, allow_partial)` → validates the `JsonValue` with `InputType::Json` → outer `prepare_validation_err(py, e, InputType::Json)`.
**Invariant:** Parse errors attach to the CALLER's original value (so `input_value='xx'`, `input_type=str`), never to an intermediate; byte-level position text comes from jiter's description of the raw slice. The funnel never re-parses per field.
**Probe:** executed live (P1, P5b): `SchemaValidator(json_schema()).validate_python('xx')` → `Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='xx', input_type=str]` — matches `tests/validators/test_json.py:63-69` id=str_invalid; direct tests: `tests/test_json.py:33-42` (accept trio + json_type), `tests/validators/test_json.py:49-94`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "map_json_err JsonInvalid description", limit: 5 });
// live rank-1: src.validators.json.map_json_err line-exact (:113)
```

## Verdict
Adopt: one coercion choke point, single parse per call, error-position text computed from raw bytes but ownership pointed at the caller's input. Adapt jiter to your parser as long as it yields (message, byte-offset). Omit nothing. Coverage: all cited paths no_recorded_issue @ gen 2026-08-25T20:09:30Z.
