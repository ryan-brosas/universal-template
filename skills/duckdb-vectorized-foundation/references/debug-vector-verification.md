<!-- capsule-v2 -->
# Debug vector verification — how does DuckDB stress-test every operator against adversarial vector encodings in production debug builds?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What encodings can `debug_verify_vector` inject, and what must the injection preserve?

## Encoding-fuzzing as an execution mode
**Path/Symbol:** `src/execution/expression_executor.cpp:ExpressionExecutor::Verify` (:168-229); enum `src/include/duckdb/common/enums/debug_vector_verification.hpp:DebugVectorVerification` (:15-24); setting `src/include/duckdb/main/settings.hpp:DebugVerifyVectorSetting` (:737-746); transforms `Vector::DebugTransformToDictionary` / `DebugShuffleNestedVector` (vector.hpp:210-212).
**Signature:** `void Verify(const Expression &expr, Vector &vector, idx_t count);` setting value type `DebugVectorVerification { NONE, DICTIONARY_EXPRESSION, DICTIONARY_OPERATOR, CONSTANT_OPERATOR, SEQUENCE_OPERATOR, NESTED_SHUFFLE, VARIANT_VECTOR, SHREDDED_VECTOR }`.
**Data Shape:** Global `DBConfigOptions::global_verification_mode` + per-session `debug_vector_verification` read at executor construction (`Settings::Get<DebugVerifyVectorSetting>(context)`, :16). Injection happens AFTER every expression execution (:306), except BOUND_REF size handling.

### Decisive source
```cpp
// :174 — dictionary-injection mode: EVERY result becomes a dictionary
if (debug_vector_verification == DebugVectorVerification::DICTIONARY_EXPRESSION) {
	Vector::DebugTransformToDictionary(vector);
}

// :177 — variant round-trip mode: cast to VARIANT and back through the real cast engine
const bool input_is_constant = vector.GetVectorType() == VectorType::CONSTANT_VECTOR;
const idx_t cast_count = input_is_constant ? 1 : count;
Vector intermediate(LogicalType::VARIANT(), cast_count);
...
VectorOperations::Cast(GetContext(), vector, intermediate, cast_count, true);
intermediate.Verify();
Vector result(vector.GetType(), cast_count);
...Cast(GetContext(), intermediate, result, cast_count, true);
if (input_is_constant) {
	result.SetVectorType(VectorType::CONSTANT_VECTOR);   // preserve constness
	FlatVector::SetSize(result, count_t(count));
}
vector.Reference(result);

// :219 — shredded mode skips constants deliberately:
//! A SHREDDED_VECTOR is never a constant vector - skip constant vectors so we don't break callers
//! that require a constant result (e.g. scalar expression folding in EvaluateScalar)
```

**Flow:** With a verification mode on, every executed expression's result is transformed into a harder encoding (dictionary-wrapped, VARIANT-round-tripped, shredded) and pushed back through `Verify()` — operators written against flat-only assumptions break loudly. Constant preservation is handled per-mode: VARIANT round-trip re-stamps CONSTANT; SHREDDED skips constants entirely.
**Invariant:** Injected transformations must preserve logical content AND observable vector class where callers depend on it (EvaluateScalar asserts CONSTANT, expression_executor.cpp:151; remap_struct relies on constant defaults — comment :189-190). This is the mechanism that makes DuckDB's "any operator must handle any VectorType" contract testable without dedicated unit tests for each pair.
**Probe:** `bash -c "grep -oE 'DICTIONARY_EXPRESSION|VARIANT_VECTOR|SHREDDED_VECTOR' src/include/duckdb/common/enums/debug_vector_verification.hpp | wc -l"` → ≥ 3 modes enumerated. Behavioral pin: sqllogictest harness wires verification into runs — `bash -c "grep -c 'GetVectorVerification() != DebugVectorVerification::NONE' test/sqlite/sqllogic_test_runner.cpp"` → ≥ 1 (actual 1 at :609).
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"DefaultSelect intermediate boolean selection","limit":5,"detail":"ids"}` anchors the surrounding executor plane (`DefaultSelect` expression_executor.cpp:368-388) that Verify wraps.

## Verdict
Adopt the pattern "run the full workload with adversarial encodings injected post-execution" verbatim — cheapest known way to smoke out format-assumption bugs in vectorized engines. Adapt the injected encodings to your engine's layouts. Omit the VARIANT/SHREDDED modes unless you port DuckDB's Variant type; note the whole plane is DEBUG-gated and absent from release behavior.
