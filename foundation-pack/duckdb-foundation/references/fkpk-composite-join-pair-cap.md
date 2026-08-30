<!-- capsule-v2 -->
# fkpk-composite-join-pair-cap — How does the estimator recognize a composite foreign-key join without declared FK metadata?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** When two columns of the same table pair are equated, how is the estimate capped at the smaller side's row count — and when must that cap NOT fire?

## Connected graph-selected seam
**Path/Symbol:** `src/optimizer/join_order/cardinality_estimator.cpp:CompositeJoinPairStats` (:144-169), `ApplyJoinPairCap` (:575-603), `ApplyJoinIncrement` (:605-635).
**Signature:** `bool ApplyJoinPairCap(double &target_denom, JoinRelationSet &join_pair, reference_map_t<JoinRelationSet, CompositeJoinPairStats> &join_pair_stats, reference_set_t<JoinRelationSet> &capped_join_pairs)`.
**Data Shape:** Per join-pair (2-relation set): `first_distinct_count` (first observed composite NDV), `max_distinct_count`, `has_distinct_count`. Cap = min of the two single-relation numerators (`GetJoinPairCap`). `MAX_CARDINALITY_TO_DISTINCT_RATIO = 8`.

### Decisive source
```cpp
	//! The row-count cap is only plausible when the candidate key cardinality is within the same order of magnitude
	//! as an observed single-column domain. Otherwise broad fact-to-fact joins can look like key lookups.
	static constexpr double MAX_CARDINALITY_TO_DISTINCT_RATIO = 8;
...
bool CardinalityEstimator::CanApplyCap(double cap) const {
	return has_distinct_count && max_distinct_count > 0 &&
	       cap <= max_distinct_count * MAX_CARDINALITY_TO_DISTINCT_RATIO;
}
```
and inside `ApplyJoinPairCap`:
```cpp
	if (cap > 0 && first_d < cap && first_d > 0) {
		// Raise weak same-pair composite evidence to the FK/PK denominator floor.
		target_denom = target_denom / first_d * cap;
		first_d = cap;
	}
```

**Flow:** every inner-equality edge registers its NDV into the pair stats of its (left∪right) set. After denominator assembly for a scope, each pair with DIRECT composite equality (both columns equated, `predicate_model.HasDirectCompositeEquality(join_pair)`) gets: cap = min(row counts); plausibility check `cap ≤ max_ndv × 8` (else it's a fact-to-fact join masquerading as FK→PK and the cap is refused); if the observed composite NDV is weaker than the row-count floor, the denominator is scaled up to the FK/PK answer (`denom/first_d×cap`). Each pair caps once (`capped_join_pairs`); same-pair equalities already accounted are skipped by `ApplyJoinIncrement` returning true WITHOUT touching the denom.
**Invariant:** The cap fires only for same-set multi-column equality pairs; transitive/redundant copies of an applied equivalence group are classified `REDUNDANT_TRANSITIVE_EQUALITY` and skipped, so one logical equality class contributes exactly one selectivity factor. Without the ×8 guard, TPC-H-style fact-to-fact joins get under-estimated by orders of magnitude.
**Probe:** `grep -n 'MAX_CARDINALITY_TO_DISTINCT_RATIO = 8' src/optimizer/join_order/cardinality_estimator.cpp` → line 148; behavior pinned by `test/optimizer/joins/fkpk_composite_key_ce.test` (:57 expects `HASH_JOIN.*~1.000 rows` for a true composite-PK join; :91+ documents the broad fact-to-fact refusal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "CompositeJoinPairStats ApplyJoinPairCap join pair distinct", limit: 8 });
```

## Verdict
Adopt the heuristic whole: direct-composite detection, min-row-count cap, ×8 plausibility gate, one-shot-per-pair accounting. Adapt the statistics source feeding `DistinctCount`. Omit the DEBUG column-name decoration. Caveat: heuristic layer has no isolated unit test; the dedicated sqllogic test pins both accept and refuse cases.
