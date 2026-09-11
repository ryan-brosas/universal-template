<!-- capsule-v2 -->
# validate_strings funnel — does `strict=True` stop string→scalar coercion in string mode?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** A porter wiring a "strict strings" entry point must know: where is the input coerced, and what does the strict flag actually control here?

## One `new_value` coercion up front, then the shared `_validate` funnel; the strict flag is DEAD at the StringMapping layer
**Path/Symbol:** `src/validators/mod.rs:SchemaValidator::validate_strings` (:285-319) + `src/input/input_string.rs` validate_* bodies (:104-255).
**Signature:** `pub fn validate_strings(&self, py, input: Bound<PyAny>, strict: Option<bool>, extra, context, allow_partial, by_alias, by_name) -> PyResult<Py<PyAny>>`.
**Data Shape:** accepts any Python object; exactly one `StringMapping::new_value(input)` decides String vs Mapping; `self_instance` is NOT a parameter (hard `None` threaded at :310); errors are prepared with `InputType::String`.

### Decisive source
```rust
let string_mapping = StringMapping::new_value(input).map_err(|e| self.prepare_validation_err(py, e, t))?;
... self._validate(py, &string_mapping, t /*InputType::String*/, strict, ...)
// input_string.rs — strict is UNUSED and results are labeled strict:
fn validate_int(&self, _strict: bool, ...) { match self {
    Self::String(s) => str_as_int(self, py_string_str(s)?).map(ValidationMatch::strict), ...
```

**Flow:** coerce once → reuse the SAME generic validation pipeline as validate_python (extra behavior, context, allow_partial, by_alias/by_name all apply identically). Because every scalar parser ignores `_strict` and self-labels `ValidationMatch::strict`, `strict=True` still converts `'1'`→1. The only observable strict difference in the direct tests comes from date-truncation rows via `TemporalUnitMode` plumbing, not the flag: `'2017-01-01T12:13:14.567'` non-strict → `date_from_datetime_inexact`, strict → `date_parsing` (:34-37).
**Invariant:** string mode's strictness lives in WHICH parsers run (always-converting shared parsers), not in a gate on conversion. A port that wires `strict` into `str_as_int`-style parsers changes union ranking (exactness labels) and breaks parity with upstream rows like int `'1'` under strict=True.
**Probe:** direct probe Q2 executed live @ pin: `SchemaValidator(int_schema()).validate_strings('1', strict=True)` → `1` (byte-matches tests/test_validate_strings.py parametrize row :24); probe Q2b `validate_strings('2017-01-01T12:13:14.567', strict=False)` on date schema → error containing `type=date_from_datetime_inexact`, matching test row :34.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "GenericPyMapping python mapping backend validate_strings", limit: 10 });
// live run this pass: SchemaValidator.validate_strings ranks 9 (mod.rs:285-319); tests/test_validate_strings.py functions cluster around it — open mod.rs range for the single-coercion shape
```

## Verdict
Adopt "coerce at the boundary once, share the pipeline" and document that strict is inert for scalar coercion in this mode; adapt the boundary to your host's CLI/config ingestion needs; omit per-call `self_instance` support (upstream omits it here). Coverage: validators/mod.rs + tests/test_validate_strings.py no_recorded_issue @ gen 2026-08-25T20:09:30Z.
