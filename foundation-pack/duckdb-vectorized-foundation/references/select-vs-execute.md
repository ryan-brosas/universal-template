<!-- capsule-v2 -->
# Select vs Execute — why do boolean expressions have a second entry point, and how does DefaultSelect work?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** When does execution materialize booleans vs. directly emit selection vectors?

## Materialize only as a last resort
**Path/Symbol:** `src/execution/expression_executor.cpp:ExpressionExecutor::Select` (:309-325) + `DefaultSelect` (:368-388) + `DefaultSelectLoop/Switch` templates (:327-366); function-side fast path `src/execution/expression_executor/execute_function.cpp:Select` (:260-316).
**Signature:** `idx_t Select(const Expression &expr, ExpressionState *state, const SelectionVector *sel, idx_t count, SelectionVector *true_sel, SelectionVector *false_sel);`
**Data Shape:** Returns survivor count; fills `true_sel` and/or `false_sel`. Only two expression classes have NATIVE select paths (BOUND_CONJUNCTION, BOUND_FUNCTION with a Select callback); everything else falls to DefaultSelect.

### Decisive source
```cpp
// :309 — dispatch: native paths only for conjunctions & functions w/ select callback
switch (expr.GetExpressionClass()) {
case ExpressionClass::BOUND_CONJUNCTION:
	return Select(expr.Cast<BoundConjunctionExpression>(), ...);
case ExpressionClass::BOUND_FUNCTION:
	return Select(expr.Cast<BoundFunctionExpression>(), ...);
default:
	return DefaultSelect(expr, state, sel, count, true_sel, false_sel);
}

// :368 — generic fallback: execute to temp stack bools, THEN build the selection
bool intermediate_bools[STANDARD_VECTOR_SIZE];
Vector intermediate(LogicalType::BOOLEAN, data_ptr_cast(intermediate_bools), STANDARD_VECTOR_SIZE);
Execute(expr, state, sel, count, intermediate);
UnifiedVectorFormat idata;
intermediate.ToUnifiedFormat(idata);
if (!sel) sel = FlatVector::IncrementalSelectionVector();
if (idata.validity.CanHaveNull()) return DefaultSelectSwitch<false>(...);  // null-aware loop
else                           return DefaultSelectSwitch<true>(...);      // NO_NULL template arm

// :332 — one pass fills BOTH output sels; result_idx preserves the OUTER mapping
auto bidx = bsel->get_index(i);          // position within intermediate
auto result_idx = sel->get_index(i);     // position in the ORIGINAL input
if ((NO_NULL || mask.RowIsValid(bidx)) && bdata[bidx] > 0)
	true_sel->set_index(true_count++, result_idx);
else if (HAS_FALSE_SEL)
	false_sel->set_index(false_count++, result_idx);
```

**Flow:** Filters call `Select`, never `Execute`+scan. Functions with a dedicated `Select()` callback (e.g. comparisons via `UnaryExecutor::Select<bool>`) evaluate per-tuple predicates straight into selections — no boolean vector exists. All-constant function args fold to ONE evaluation then `SelectBooleanResult` broadcasts (:284-305). Conjunctions thread selections adaptively (see adaptive-filter capsule). Everything else pays one flat boolean vector + a gather pass.
**Invariant:** Emitted indices are ALWAYS in terms of the caller's ORIGINAL tuple space (`result_idx = sel->get_index(i)`), not the intermediate's — getting this wrong shifts every subsequent operator by the incoming filter. NULL handling is branch-selected by `validity.CanHaveNull()`: the NO_NULL template arm skips mask reads entirely.
**Probe:** `bash -c "grep -c 'DefaultSelectSwitch' src/execution/expression_executor.cpp"` → ≥ 2 (both NO_NULL arms). Behavioral pin: `test/sql/conjunction/or_comparison.test` pins OR-filter correctness under outer selection.
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"DefaultSelect intermediate boolean selection","limit":5,"detail":"ids"}` resolves `DefaultSelect` :368-388 line-exact.

## Verdict
Adopt the dual-entry contract (Execute→vector, Select→selection) and the outer-space index mapping verbatim. Adapt which expression classes get native select paths to your predicate mix. Omit the stack-allocated `intermediate_bools[STANDARD_VECTOR_SIZE]` micro-optimization if your vector width differs — allocate normally.
