<!-- capsule-v2 -->
# CASE execution — how do you evaluate a CASE expression so each branch runs only on the tuples that reach it?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How are surviving/failing tuple sets threaded through WHEN clauses and scattered into one result vector?

## Selection-driven branch evaluation
**Path/Symbol:** `src/execution/expression_executor/execute_case.cpp:ExpressionExecutor::Execute` (BoundCaseExpression, :34-93); scatter `FillSwitch` (:147-230); loops `TemplatedFillLoop<T>` (:95-123) / `ValidityFillLoop` (:125-145).
**Signature:** `void Execute(const BoundCaseExpression &expr, ExpressionState *state_p, const SelectionVector *sel, idx_t count, Vector &result); void FillSwitch(const Vector &vector, Vector &result, const SelectionVector &sel, sel_t count);`
**Data Shape:** `CaseExpressionState` owns two reusable `SelectionVector true_sel/false_sel` of STANDARD_VECTOR_SIZE plus `intermediate_chunk` sized `2*checks+1` (when/then pairs + else). Branch results land in `intermediate_chunk.data[i*2+1]`, else in `data[checks*2]`.

### Decisive source
```cpp
// :45 — the funnel: current_sel/current_count = tuples no earlier branch claimed
for (idx_t i = 0; i < expr.CaseChecks().size(); i++) {
	idx_t tcount = Select(*case_check.when_expr, check_state, current_sel, current_count,
	                      current_true_sel, current_false_sel);
	if (tcount == 0) continue;                       // nobody matched: next WHEN
	idx_t fcount = current_count - tcount;
	if (fcount == 0 && current_count == count) {
		// everything is true in the first CHECK statement:
		// skip the entire case and only execute the TRUE side
		Execute(*case_check.then_expr, then_state, sel, count, result);
		return;                                      // fast path
	}
	Execute(*case_check.then_expr, then_state, current_true_sel, tcount, intermediate_result);
	FillSwitch(intermediate_result, result, *current_true_sel, NumericCast<sel_t>(tcount));
	current_sel = current_false_sel;                 // continue with the false tuples
	current_count = fcount;
	if (fcount == 0) break;                          // everything is true: done
}
...
if (sel) result.Slice(*sel, count);                  // re-apply OUTER selection at the very end
```

**Flow:** Each WHEN's Select splits the incoming (already-narrowed) tuple set into matched/unmatched. Matched tuples get their THEN evaluated ONLY on them and the result SCATTERED into the final vector through the true-sel (`FillSwitch` writes `res[sel.get_index(i)]`). Unmatched become the input of the next WHEN; leftovers fall to ELSE. The outer `sel` is re-applied to the result at the end (:90-92).
**Invariant:** THEN expressions must be safe on their matched tuples only — this is what makes `case when x<>'' then cast(...) end` not error on empty x (short-circuit semantics live HERE, not in the optimizer). `TemplatedFillLoop` handles CONSTANT branch results specially (broadcast via `*data`, null → SetInvalid per index), VARCHAR fills require `StringVector::AddHeapReference(result, vector)` (:189-192) to keep referenced string heap alive, STRUCT recurses per child after optional Flatten (:193-206), LIST appends child data then offsets entries by prior list size (:207-226).
**Probe:** `bash -c "grep -c 'FillSwitch' src/execution/expression_executor/execute_case.cpp"` → ≥ 3 (definition + two call sites). Behavioral pin: `test/sql/function/generic/case_short_circuit.test` — `cast(substr(n,1,1) as int)` never sees the `(empty)` row.
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"FillSwitch TemplatedFillLoop case expression","limit":6,"detail":"ids"}` resolves `FillSwitch` :147-230 and `TemplatedFillLoop` :95-123 line-exact.

## Verdict
Adopt selection-threaded CASE with the all-true fast path and the trailing outer-sel Slice verbatim. Adapt `FillSwitch`'s physical-type switch to your type system; keep the CONSTANT-broadcast and LIST-offset special cases if you support nested types. Omit DuckDB's ARRAY/INTERVAL/hugeint template instantiations you don't carry.
