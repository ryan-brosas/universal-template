<!-- capsule-v2 -->
# Cardinality estimator algebra — how are min/exp/max match counts combined through a filter tree?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** Given per-condition estimates, what exact formulas produce must/should/min_should/must_not cardinalities, and when do primary clauses survive?

## Filter-tree estimation algebra
**Path/Symbol:** `lib/segment/src/index/query_estimator.rs`: `adjust_to_available_vectors` (:26-66), `expected_should_estimation` (:119-131), `combine_should_estimations` (:133-154), `combine_min_should_estimations` (:161-185), `combine_must_estimations` (:187-220), `estimate_filter` (:243-282), `invert_estimation` (:328-338), `estimate_must_not` (:340-354).
**Signature:** `pub fn estimate_filter<F>(estimator: &F, filter: &Filter, total: usize) -> OperationResult<CardinalityEstimation>` where `F: Fn(&Condition) -> OperationResult<CardinalityEstimation>`; `CardinalityEstimation{primary_clauses, min, exp, max}`.
**Data Shape:** recursive closure over conditions; leaves return indexed-field estimates; internal nodes combine; `primary_clauses` carry the best index plan (e.g. smallest-exp must branch).

### Decisive source
```rust
// MUST: independent-intersection model
let min_estimation = estimations.iter().map(|x| x.min)
    .fold(total as i64, |acc, x| max(0, acc + (x as i64) - (total as i64))) as usize; // inclusion-exclusion floor
let max_estimation = estimations.iter().map(|x| x.max).min().unwrap_or(total);
let exp_estimation = (estimations.iter().map(|x| (x.exp as f64)/(total as f64)).product::<f64>() * total as f64).round() as usize;
let clauses = estimations.iter().filter(|x| !x.primary_clauses.is_empty())
    .min_by_key(|x| x.exp).map(|x| x.primary_clauses.clone()).unwrap_or_default(); // SMALLEST exp wins

// SHOULD: complement rule  (1 - ∏(1-pᵢ)) * total
// min = max of branch mins, max = min(sum of maxes, total)
for estimation in estimations { if estimation.primary_clauses.is_empty() {
    // If some branch is un-indexed - we can't make any assumptions about the whole `should` clause
    clauses = vec![]; break; } }

// MIN_SHOULD: estimate all C(n, min_count) intersections, then combine as should
if min_count > estimations.len() { return Ok(CardinalityEstimation::exact(0)); }

// MUST_NOT: invert each child then combine as must
invert_estimation: min = total - est.max; exp = total - est.exp; max = total - est.min; clauses = vec![]
```

**Flow:** `estimate_filter` evaluates the four clause families in order must → should → min_should → must_not and finally combines THOSE with `combine_must_estimations` (a filter behaves like an intersection of its parts) → deleted-vector correction via `adjust_to_available_vectors(est, available_vectors, available_points)`: `exp *= available_vectors/available_points`, `min -= deleted_count` saturating, `max = min(max, available_vectors, available_points)`; `adjust_for_deferred_points` is the same shape for deferred visibility.
**Invariant:** (1) one unindexed SHOULD branch voids ALL primary clauses but leaves numeric bounds intact — plans degrade to full scan silently, by design; (2) MUST picks the single smallest-exp clause list, never unions them; (3) min_count > len returns exact(0) BEFORE generating combinations (prevents pathological allocation); (4) min_should with min_count == len must equal must exactly (pinned by test); (5) debug asserts enforce min ≤ exp ≤ max after adjustment.

**Probe:** `grep -c "#\[test\]" lib/segment/src/index/query_estimator.rs` → prints `12`. Direct tests: `simple_query_estimation_test` (:451), `must_estimation_query_test` (:459), `another_should_estimation_query_test` (:500, pins clause-voiding), `combine_min_should_min_count_above_len_returns_exact_zero` (:551), `min_should_with_min_count_same_as_condition_count_is_equivalent_to_must` (:563), `test_adjust_to_available_vectors` (:676); integration twins `payload_index_test.rs::test_cardinality_estimation` (:823).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "estimate_filter combine_must_estimations combine_should_estimations adjust_to_available_vectors", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the formulas verbatim (they are pure functions). Adapt the leaf estimator closure to host field indexes; keep primary-clause semantics (void on unindexed should, min-exp selection on must). Omit nothing portable — this file is self-contained.
