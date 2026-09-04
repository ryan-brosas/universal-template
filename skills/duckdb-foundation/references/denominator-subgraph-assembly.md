<!-- capsule-v2 -->
# denominator-subgraph-assembly — How is the join denominator built when predicates only cover disconnected parts of the relation set?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the algorithm that turns per-predicate selectivity into one denominator for an N-relation set, including cross-product gaps?

## Connected graph-selected seam
**Path/Symbol:** `src/optimizer/join_order/cardinality_estimator.cpp:GetDenominator` (:880-887), `ProcessDenominatorEdge` (:720-762), `SubgraphsConnectedByEdge` (:393-422), `CreateDenominatorResult` (:869-878).
**Signature:** `DenomInfo GetDenominator(JoinRelationSet &set)`; numerator ÷ denominator then cached in `relation_set_2_cardinality`.
**Data Shape:** `DenominatorState`: `vector<Subgraph2Denominator> subgraphs` (each: relations set, numerator_relations set, denom double), `applied_equivalence_groups`, `join_pair_stats`, `capped_join_pairs`, `unused_edge_tdoms`.

### Decisive source
```cpp
double CardinalityEstimator::CalculateInnerJoinDenom(double base_denom, FilterInfoWithTotalDomains &filter) {
	auto effective_d = filter.GetDistinctCount();
	auto comparison_type = filter.GetComparisonType();
	if (comparison_type == ExpressionType::INVALID) {
		return base_denom * effective_d;
	}
	return ApplyComparisonRatio(base_denom, comparison_type, effective_d);
}
```
with `ApplyComparisonRatio` (:446-462): equality/not-distinct multiplies by `effective_d`; range/inequality by `pow(effective_d, 2.0 / 3.0)`.

**Flow:** edges sorted by descending tdom (`SortTdoms`) are streamed through `ProcessDenominatorEdge`; each edge either creates a subgraph, extends exactly one, merges two, or is absorbed as redundant-transitive. After all edges: disconnected subgraphs merge by cross product (`MergeDisconnectedDenominatorSubgraphs` multiplies denoms), uncovered relations are added via `AddCrossProductRelations`, unused reliable domains each multiply the final denom by (1 + count) in `CreateDenominatorResult` — a penalty so unexploited filter knowledge shrinks the estimate. SEMI/ANTI multiply the appropriate side's denom by `DEFAULT_SEMI_ANTI_SELECTIVITY = 5` (cardinality_estimator.hpp:28); LEFT joins take max(inner estimate, preserved-side estimate) in `CalculateLeftJoinDenomInfo`.
**Invariant:** Numerator and denominator sides must track DIFFERENT relation sets for semi/anti joins — `GetNumerator(denom.numerator_relations)` deliberately excludes RHS cardinalities ("for semi and anti joins, we don't want to include cardinalities of relations on the RHS"). Results memoize into `relation_set_2_cardinality`; a cached entry short-circuits denominator assembly entirely.
**Probe:** `grep -c 'CROSS_PRODUCT' test/optimizer/joins/denominator_cardinality_estimation.test` → 1 (disconnected-component merge case); `grep -n 'Equality components can be discovered' test/optimizer/joins/denominator_cardinality_estimation.test` → line 44.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "GetDenominator ProcessDenominatorEdge SubgraphsConnectedByEdge", limit: 8 });
```

## Verdict
Adopt the subgraph create/extend/merge state machine plus the pow(d, ⅔) range selectivity and unused-domain penalty. Adapt predicate classification to host expression model. Omit DEBUG name printing. Caveat: covered by dedicated sqllogic suite (denominator_cardinality_estimation), no C++ unit test.
