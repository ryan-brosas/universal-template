<!-- capsule-v2 -->
# Constant-vector folding — how does a whole chunk of one value cost O(1), and when must folding be suppressed?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the exact constant-propagation protocol in expression execution, and which functions are excluded?

## One evaluation per chunk
**Path/Symbol:** `src/execution/expression_executor/execute_function.cpp:ExpressionExecutor::Execute` (BoundFunctionExpression, :201-258); volatile guard :206-210; restore :245-253.
**Signature:** `void Execute(const BoundFunctionExpression &expr, ExpressionState *state, const SelectionVector *sel, idx_t count, Vector &result)`.
**Data Shape:** Arguments live in `state->intermediate_chunk.data[i]` (reused per call via `Reset()`). A CONSTANT_VECTOR stores ONE element with buffer size 1 but reports `FlatVector::SetSize(v, count)` — logical length is decoupled from storage.

### Decisive source
```cpp
// :205 — the fold gate
bool all_constant = true;
if (expr.Function().GetStability() == FunctionStability::VOLATILE) {
	// we cannot optimize away constant vectors for volatile functions
	all_constant = false;                    // random()/random_normal() MUST run count times
}
...
if (all_constant) {
	// if all arguments are constant temporarily set the child cardinality to 1
	arguments.SetChildCardinality(1ULL);
} else {
	arguments.SetChildCardinality(count);
}
...
if (all_constant) {                          // :245 restore + constant result
	for (auto &arg : arguments.data) arg.SetVectorType(VectorType::CONSTANT_VECTOR);
	arguments.SetChildCardinality(count);
	result.FlattenAndSetConstant();          // materialize 1 row, mark CONSTANT again
}
FlatVector::SetSize(result, count_t(count)); // logical length = input length ALWAYS
```

**Flow:** (1) execute each child into the reused argument chunk; (2) any non-constant child → `all_constant=false`; (3) all-constant → run the callback ONCE on cardinality 1; (4) restore child cardinality and re-stamp every argument CONSTANT (the function may have flattened them); (5) force the RESULT to a size-`count` constant vector. Constant-NULL short-circuit: a NULL constant arg under DEFAULT_NULL_HANDLING returns `ConstantVector::SetNull(result, count)` immediately (:216-222).
**Invariant:** The result of an all-constant execution has vector type CONSTANT and logical size == input count; consumers may rely on `result.GetVectorType()==CONSTANT_VECTOR` after folding (EvaluateScalar asserts it, expression_executor.cpp:151). VOLATILE functions are never folded even if all args are constants. Cardinality juggling is temporary — leaving `SetChildCardinality(1)` stuck would corrupt downstream operators.
**Probe:** `bash -c "grep -c 'FunctionStability::VOLATILE' src/execution/expression_executor/execute_function.cpp"` → ≥ 2 (Execute AND Select paths both gate). Behavioral pin: `test/sql/function/generic/case_short_circuit.test` proves side-effecting casts inside CASE still evaluate exactly once per branch entry.
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"ConstantVector SetNull validity mask","limit":5,"detail":"ids"}` resolves `ConstantVector.SetNull` constant_vector.cpp:58-87 and the validity plumbing line-exact.

## Verdict
Adopt the fold-once/restore-cardinality/stamp-result protocol verbatim for any scalar pipeline. Adapt the `FunctionStability` enum vocabulary to your host's volatility classification. Omit DuckDB's debug `VerifyNullHandling` hook (debug builds only, :148-181) unless you port the verification framework too.
