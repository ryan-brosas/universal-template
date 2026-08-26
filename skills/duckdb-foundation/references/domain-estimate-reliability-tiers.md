<!-- capsule-v2 -->
# domain-estimate-reliability-tiers — Which distinct-count do you trust when several sources disagree?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How are conflicting NDV (distinct-count) estimates from different provenance merged into one domain value?

## Connected graph-selected seam
**Path/Symbol:** `src/optimizer/join_order/cardinality_estimator.cpp:DomainEstimate` (:29-87), sources checked at :45-47.
**Signature:** `void Update(const DistinctCount &distinct_count)` / `idx_t GetDistinctCount() const`.
**Data Shape:** Three slots: `optional_idx reliable_distinct_count` (HLL or EXACT provenance), `optional_idx min_max_distinct_count`, `idx_t fallback_distinct_count` (initialized to `NumericLimits<idx_t>::Maximum()`). `DistinctCountSource::HLL | EXACT | MIN_MAX | <other>`.

### Decisive source
```cpp
void DomainEstimate::Update(const DistinctCount &distinct_count) {
	if (IsReliableDistinctCount(distinct_count.source)) {
		UpdateMaxDistinctCount(reliable_distinct_count, distinct_count.distinct_count);
	} else if (distinct_count.source == DistinctCountSource::MIN_MAX) {
		UpdateMaxDistinctCount(min_max_distinct_count, distinct_count.distinct_count);
	} else {
		fallback_distinct_count = MinValue(distinct_count.distinct_count, fallback_distinct_count);
	}
}
```

**Flow:** every column statistic feeding a join predicate updates the shared domain group: reliable sources take a MAX within their tier; MIN_MAX takes max within its tier; everything else (unreliable heuristics) takes a MIN against +infinity. Read-back precedence is reliable → min-max → fallback. So higher-trust tiers always win wholesale, and within a tier NDVs are combined optimistically (max) for trusted data, pessimistically (min) for untrusted.
**Invariant:** Tier selection happens per update, not at read time; a single HLL observation permanently dominates any number of heuristic ones. The fallback slot must start at idx_t MAX so the first `MinValue` wins — initializing to 0 would collapse all estimates to 0 and zero out join cardinalities.
**Probe:** `grep -n 'IsReliableDistinctCount(DistinctCountSource source)' src/optimizer/join_order/cardinality_estimator.cpp` → line 45; `grep -c 'DEFAULT_SELECTIVITY = 0.2' src/include/duckdb/optimizer/relation_statistics/relation_statistics_helper.hpp` → 1 (the OR-filter selectivity constant used alongside); behavior pinned by `test/optimizer/joins/better_ce_estimates_for_bad_join_conditions.test` and `test/optimizer/joins/parquet_minmax_cardinality_estimation.test`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "DomainEstimate Update distinct count HLL MIN_MAX", limit: 8 });
```

## Verdict
Adopt the tiered merge (trusted-max, minmax-max, fallback-min, tier-wins-at-read). Adapt source enum names to host stats metadata. Omit debug-only relation-name decoration (`AddRelationNamesToRelationStats` is DEBUG-gated). Caveat: header `cardinality_estimator.hpp` coverage freshness reads "missing" in check_index_coverage while the .cpp is clean — verify spans via search_graph when citing header lines.
