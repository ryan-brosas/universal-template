<!-- capsule-v2 -->
# Function validators — what execution order do before/after/plain/wrap guarantee and how do errors convert?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** For each function-* schema type, exactly when does user code run relative to inner validation, and what happens to its Python exceptions?

## before=py-then-inner, after=inner-then-py, plain=user-replaces-all, wrap=user-controls-handler
**Path/Symbol:** `src/validators/function.rs` (whole file): FunctionBeforeValidator :85-156, FunctionAfterValidator :158-241, FunctionPlainValidator :232-292, FunctionWrapValidator :294-400; `convert_err` :507.
**Signature:** shared `destructure_function_schema` reads nested `{function: {type: with-info|no-info, function, ...}}`; `info_arg` selects whether ValidationInfo is passed. Wrap's handler receives `(input, handler)` or `(input, handler, info)`.
**Data Shape:** ValidationInfo carries data (accumulated fields dict), config, field_name — field_name resolution prefers CURRENT state.extra().field_name, falling back to schema-captured one (:104-111).

### Decisive source
```rust
// BEFORE: user transforms input first; result feeds inner validation
let value = r.map_err(|e| convert_err(py, e, input))?;
call(value.into_bound(py), state)      // call = self.validator.validate(...)
// AFTER: inner validates first; user receives VALIDATED value
let v = call(input, state)?;
let r = ... self.func.call1(py, (v, info)); r.map_err(|e| convert_err(py, e, input))
// WRAP: user gets a callable pyo3 object bound to the inner validator
self.func.call1(py, (input.to_object(py)?, handler, info))
// afterwards state metrics are copied back from the handler:
state.exactness = handler.validator.exactness;
state.fields_set_count = handler.validator.fields_set_count;
```

**Flow:** All four funnel Python exceptions through `convert_err`: PydanticOmit ⇒ ValError::Omit; PydanticUseDefault ⇒ ValError::UseDefault; PydanticCustomError ⇒ custom ErrorType; anything else ⇒ InternalErr (propagates as-is — NOT wrapped into ValidationError lines). Wrap's handler is an `InternalValidator` (borrowed from generator.rs :218+) pyclass so USER CODE drives inner validation lazily; exactness/fields_set_count are synced back AFTER the call because the user may invoke the handler zero or multiple times. before/after also forward validate_assignment symmetrically (assignment flows through the SAME user functions).
**Invariant:** Plain validators never touch definitions (build ignores them) — they replace inner validation entirely. Wrap must restore metrics even on failure (they're read unconditionally post-call). User functions always receive PYTHON objects (`input.to_object`) — Rust-side input representations never leak.
**Probe:** `grep -n 'fn convert_err' src/validators/function.rs` =1 (:507); `grep -cn 'PydanticOmit\|PydanticUseDefault' src/validators/function.rs` ≥4; direct tests: tests/validators/test_function.py green this pass (in 283 batch).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "FunctionWrapValidator InternalValidator handler", limit: 5 });
// live rank-family: function.rs classes resolve line-exact
```

## Verdict
Adopt: the four-ordering contract verbatim, exception-kind conversion table (omit/use-default/custom/internal), metric sync-back after wrap. Adapt handler plumbing if you lack pyo3-style pyclasses — a closure/callable pair works. Omit config snapshotting details (ValidationInfo construction) to your host's config shape.
