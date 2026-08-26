<!-- capsule-v2 -->
# left-join-input-cost-correction — Why is a LEFT join never cost-free even though its output cardinality equals the LHS?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does the cost model stop the optimizer from scheduling all LEFT joins first?

## Connected graph-selected seam
**Path/Symbol:** `src/optimizer/join_order/cost_model.cpp:ComputeCost` (:40-48) and `GetLeftJoinInputCost` (:17-35).
**Signature:** `double ComputeCost(DPJoinNode &left, DPJoinNode &right, JoinRelationSet &combination, const vector<reference<NeighborInfo>> &possible_connections)`.
**Data Shape:** Cost = `EstimateCardinalityWithSet<double>(combination)` + optional LEFT correction + `left.cost + right.cost`. `possible_connections` are the hyper-graph edges between the two sets; each carries join predicates with `GetJoinType()` and a right-side relation set.

### Decisive source
```cpp
// Currently cost of a join mostly factors in the cardinalities.
// LEFT joins need an explicit RHS input component because their output cardinality preserves the LHS,
// which otherwise makes early LEFT joins over large RHS inputs look almost free.
double CostModel::ComputeCost(DPJoinNode &left, DPJoinNode &right, JoinRelationSet &combination,
                              const vector<reference<NeighborInfo>> &possible_connections) {
	auto join_card = cardinality_estimator.EstimateCardinalityWithSet<double>(combination);
	auto join_cost = join_card;
	if (query_graph_manager.GetPredicateModel().HasLeftJoinPredicates()) {
		join_cost += GetLeftJoinInputCost(cardinality_estimator, possible_connections);
	}
	return join_cost + left.cost + right.cost;
}
```

**Flow:** base cost is estimated output cardinality of the combined set. When ANY left-join predicate exists in the model, `GetLeftJoinInputCost` walks the candidate connections, dedups right sides via `reference_set_t` (`seen_right_sides.insert(...).second` — second insert of the same right set is SKIPPED), and adds `EstimateCardinalityWithSet<double>(right_set)` per distinct RIGHT side. So a LEFT join whose preserved LHS is tiny but whose RHS input is huge pays for the RHS.
**Invariant:** The correction is gated on `HasLeftJoinPredicates()` (zero overhead when no LEFT joins exist), applies ONLY to predicates with `JoinType::LEFT`, and counts each distinct right side once. Porting the naive "cost = output cardinality" without this term makes greedy/DP orderings defer small LEFT joins and eagerly build giant cross products instead.
**Probe:** `grep -n 'GetLeftJoinInputCost' src/optimizer/join_order/cost_model.cpp` → lines 17 (definition) and 45 (call site); behavior pinned by `test/optimizer/joins/left_join_reordering/test_reordering_left_joins.test`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "ComputeCost GetLeftJoinInputCost left join cardinality", limit: 8 });
```

## Verdict
Adopt the RHS-input surcharge semantics and the dedup-by-right-set detail. Adapt the estimator call to host statistics API. Omit the D_ASSERT on right-set optionality (debug-only). Caveat: file fully indexed, no parse flags; covered by left-join reordering suite rather than a dedicated unit test.
