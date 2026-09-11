<!-- capsule-v2 -->
# art-try-initialize-scan-predicate-ladder — Which WHERE clauses can an ART index scan serve, and what are the exact refusals?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does the optimizer decide, per filter expression, whether a point/range index scan applies — including the IS NOT DISTINCT FROM NULL trap?

## Connected graph-selected seam
**Path/Symbol:** `src/execution/index/art/art.cpp:TryInitializeScan` (:155-256).
**Signature:** `unique_ptr<IndexScanState> TryInitializeScan(const Expression &expr, const Expression &filter_expr)`.
**Data Shape:** `ARTIndexScanState` holds `Value values[2]` + `ExpressionType expressions[2]`; `values[0].IsNull()` later signals FULL scan. Matcher: comparison with one indexed-expression side and one constant side (`SetMatcher::Policy::UNORDERED`).

### Decisive source
```cpp
		if (comparison_type == ExpressionType::COMPARE_NOT_DISTINCT_FROM) {
			// Table filters discard NULL and false alike, so IS NOT DISTINCT FROM a
			// non-NULL constant selects the same rows as equality. NULL is not indexed.
			if (constant_value.IsNull()) {
				return nullptr;
			}
			equal_value = constant_value;
		} else if (comparison_type == ExpressionType::COMPARE_EQUAL) {
			// An equality value overrides any other bounds.
			equal_value = constant_value;
		}
```

**Flow:** match `<indexed expr> <cmp> <constant>` (either orientation; flip comparison when constant is on the left) → classify: EQUAL / IS-NOT-DISTINCT-FROM → equality override; GT/GE → lower bound; else upper bound. BETWEEN handled separately requiring BOTH bounds constant. Refusals (`return nullptr`, fall back to table scan): non-constant operand, `IS NOT DISTINCT FROM NULL` (NULLs unindexed), equality-with-NULL, no bound found. Final selection: equality alone wins over any range pair; low+high → two-predicate close-range state.
**Invariant:** Equality OVERRIDES previously collected bounds (assignment order in the ladder), and the INDLF-null refusal is load-bearing: table filters treat NULL like false, so pushing `IS NOT DISTINCT FROM NULL` into the ART would silently drop rows the query must return. Scan dispatch (`ART::Scan` :781-820) then routes on `values[0].IsNull()` → full scan; single value → SearchEqual/Greater/Less by expression type; two values → SearchCloseRange with inclusivity flags.
**Probe:** `grep -n 'IS NOT DISTINCT FROM NULL matches NULL' test/sql/index/art/scan/test_not_distinct_index_scan.test` → line 26; also covered by `test/sql/index/art/scan/test_not_distinct_index_scan.test:12` EXPLAIN ANALYZE showing INDEX_SCAN for the non-null case.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "TryInitializeScan IndexScanState COMPARE_NOT_DISTINCT_FROM", limit: 8 });
```

## Verdict
Adopt the classification ladder with all three refusal branches verbatim. Adapt matcher framework to host expression matching. Omit the FIXME about rewritten BETWEEN (CONJUNCTION_AND form not yet matched). Caveat: art.cpp fully indexed; dedicated sqllogic test pins both the served and refused INDLF cases.
