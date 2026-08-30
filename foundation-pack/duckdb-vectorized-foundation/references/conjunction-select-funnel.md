<!-- capsule-v2 -->
# Conjunction Select funnel — how does an AND/OR chain evaluate each predicate only on the tuples that still qualify?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the exact selection-threading for AND vs OR chains, including the temp-sel juggling?

## Shrinking candidate set, one predicate at a time
**Path/Symbol:** `src/execution/expression_executor/execute_conjunction.cpp:ExpressionExecutor::Select` (BoundConjunctionExpression, :61-146); Execute fallback (:33-59); order source `AdaptiveFilter::GetPermutation`.
**Signature:** `idx_t Select(const BoundConjunctionExpression &expr, ExpressionState *state_p, const SelectionVector *sel, idx_t count, SelectionVector *true_sel, SelectionVector *false_sel);`
**Data Shape:** Temp `SelectionVector(STANDARD_VECTOR_SIZE)` allocated ONLY when the caller didn't pass the opposite output (AND: needs temp_false if caller wants false_sel; OR: needs temp_true symmetrically).

### Decisive source
```cpp
// :66 — AND: survivors shrink monotonically; failures accumulate into false_sel
for (idx_t i = 0; i < expr.GetChildren().size(); i++) {
	idx_t tcount = Select(*children[permutation[i]], child_states[permutation[i]].get(),
	                      current_sel, current_count, true_sel, temp_false.get());
	idx_t fcount = current_count - tcount;
	if (fcount > 0 && false_sel) {
		for (idx_t i = 0; i < fcount; i++)
			false_sel->set_index(false_count++, temp_false->get_index(i));
	}
	current_count = tcount;
	if (current_count == 0) break;
	if (current_count < count) current_sel = true_sel;   // later predicates see ONLY survivors
}
...
return current_count;

// :106 — OR: failures shrink; passes accumulate into true_sel ...
tcount = Select(..., current_sel, current_count, temp_true.get(), false_sel);
if (tcount > 0) { ...append temp_true into true_sel...; current_count -= tcount; current_sel = false_sel; }
...
if (true_sel) true_sel->Sort(result_count);              // :138 — restore ascending tuple order!
```

**Flow:** AND walks children (in adaptive permutation order): each child selects within the surviving set; the true-sel of step N becomes the input sel of step N+1 once anything was filtered (`current_count < count` guard avoids needless switching on the first predicate). Failures from every step append to the caller's false_sel. OR is its dual: unmatched tuples continue, matched accumulate; because OR's accumulated true-sel ends up unsorted (tuple indices appended in discovery order), it is explicitly `Sort()`ed before returning. The non-select `Execute` path (:33-59) simply folds children two-at-a-time via `VectorOperations::And/Or` with a reference-and-replace pattern.
**Invariant:** Every child sees a subset of its parent's input and outputs indices in the ORIGINAL tuple space; AND must not reorder true_sel (it stays sorted by construction), while OR MUST sort or downstream binary-search/order-sensitive operators break. Early exit when `current_count == 0` is legal because further predicates cannot revive tuples.
**Probe:** `bash -c "grep -c 'current_sel = true_sel\|current_sel = false_sel' src/execution/expression_executor/execute_conjunction.cpp"` → ≥ 2 (one per branch). Behavioral pin: `test/sql/conjunction/or_between.test` + `or_comparison.test` (issue-3659 result-equivalence regressions).
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"ConjunctionState adaptive filter conjunction execute","limit":5,"detail":"ids"}` resolves `ConjunctionState` :12-20 and `Execute` :33-59 line-exact.

## Verdict
Adopt the AND/OR duality with the sort-on-OR rule verbatim. Adapt the adaptive permutation hook (drop it to get a static-order evaluator). Omit DuckDB's logging of filter reordering events (AdaptiveFilterLogType) unless you port the logging framework.
