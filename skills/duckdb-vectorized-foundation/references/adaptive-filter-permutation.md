<!-- capsule-v2 -->
# Adaptive filter permutation — how do AND/OR conjunctions learn their cheapest evaluation order at runtime?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the swap-trial-revert algorithm, and which safety conditions disable reordering?

## Runtime filter-order learning
**Path/Symbol:** `src/execution/adaptive_filter.cpp:AdaptiveFilter` (:15-178); state holder `src/include/duckdb/execution/adaptive_filter.hpp:AdaptiveFilter` (permutation :57, swap_likeliness :58); consumer `src/execution/expression_executor/execute_conjunction.cpp:ConjunctionState` (:12-20) + `Select` (:61-146).
**Signature:** `AdaptiveFilter::AdaptiveFilter(const Expression &expr)`; `void AdaptRuntimeStatistics(double duration); const vector<idx_t> &GetPermutation() const;`
**Data Shape:** `permutation : vector<idx_t>` (child order), `swap_likeliness : vector<idx_t>` per adjacent pair (starts 100), `observe_interval=10`, `execute_interval=20`, `warmup=true` for the first 5 calls, `right_random_border = 100 * (n_children - 1)`.

### Decisive source
```cpp
// cpp:15 — SAFETY: a child that can throw must never be reordered
for (idx_t idx = 0; idx < conj_expr.GetChildren().size(); idx++) {
	permutation.push_back(idx);
	if (conj_expr.GetChildren()[idx]->CanThrow()) {
		disable_permutations = true;
	}
	...
}

// cpp:107 — the learning loop (runs once per executed filter)
if (!observe && iteration_count == execute_interval) {
	prev_mean = runtime_sum / iteration_count;
	auto random_number = generator.NextRandomInteger(1, right_random_border);
	swap_idx = random_number / 100;                     // which adjacent pair
	idx_t likeliness = random_number - 100 * swap_idx;  // trial threshold [0,100)
	if (swap_likeliness[swap_idx] > likeliness) {       // always true first time
		std::swap(permutation[swap_idx], permutation[swap_idx + 1]);
		observe = true;                                 // measure this trial
	}
	...
} else if (observe && iteration_count == observe_interval) {
	auto trial_mean = runtime_sum / iteration_count;
	if (prev_mean - trial_mean <= 0) {
		std::swap(permutation[swap_idx], permutation[swap_idx + 1]); // REVERT: no speedup
		if (swap_likeliness[swap_idx] > 1) swap_likeliness[swap_idx] /= 2; // decay
	} else {
		swap_likeliness[swap_idx] = 100;                // KEEP: reset likeliness
	}
	observe = false;
}
```

**Flow:** warmup(5 filters) → every 20 filters pick random adjacent pair weighted by `swap_likeliness`, apply swap → next 10 filters time both orders → keep if mean latency dropped, else revert and halve that pair's likeliness. The CONSUMER side (execute_conjunction.cpp:66-105) walks children in `permutation` order, feeding survivors forward: after the first child filters tuples out (`current_count < count`) it switches `current_sel = true_sel` so later predicates only evaluate surviving tuples; OR mirrors it through `false_sel` and sorts the accumulated true-sel at the end (:138-140).
**Invariant:** Reordering is legal only because each child is evaluated on exactly the tuple set the previous children passed — semantics of AND/OR are preserved by selection-threading, NOT by commutativity assumptions; any throwing child (`CanThrow()`, e.g. casts that can error) disables permutations entirely (`BeginFilter`/`EndFilter` early-return when `disable_permutations || permutation.size() <= 1`). Single-child or disabled conjunctions never adapt.
**Probe:** `bash -c "grep -c 'disable_permutations' src/execution/adaptive_filter.cpp"` → ≥ 4 (ctor sets it; BeginFilter+EndFilter guard on it). Behavioral pin: `test/sql/conjunction/or_between.test` (issue 3659 regression: OR-of-BETWEEN result correctness under reordered evaluation).
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"AdaptiveFilter permutation swap likeliness","limit":6,"detail":"ids"}` resolves fields hpp:57-58 and ctor cpp:30-38 line-exact.

## Verdict
Adopt the swap/observe/revert-with-decay loop and the CanThrow veto verbatim — it ports to any conjunctive-filter evaluator. Adapt the RNG source, timing clock (`TimePoint::Tick` monotonic), and logging hooks to your host. Omit the TableFilterSet constructor variant (:30-38) unless you also port DuckDB's pushdown filter plan; note `Remap()` (:40-63) exists for filter-set swaps across rebinds.
