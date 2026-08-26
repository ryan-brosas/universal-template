<!-- capsule-v2 -->
# equal-cost-right-cardinality-tiebreaker — Why do equal-cost DP plans get replaced, and why does that matter only for LEFT joins?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the DP-table replacement rule when a new plan's cost exactly equals the stored plan's cost?

## Connected graph-selected seam
**Path/Symbol:** `src/optimizer/join_order/plan_enumerator.cpp:EmitPair` (:192-235), tiebreaker block (:218-232).
**Signature:** `optional_ptr<DPJoinNode> EmitPair(JoinRelationSet &left, JoinRelationSet &right, const vector<reference<NeighborInfo>> &info)`.
**Data Shape:** `plans[new_set]` holds the incumbent `DPJoinNode` (fields: cost double, cardinality idx_t, left_set/right_set). `old_cost` initializes to `double::Maximum()` when the set is unoccupied.

### Decisive source
```cpp
	// Tiebreaker for equal-cost plans: needed for LEFT JOINs,
	// because all orderings preserve the LHS cardinality and always tie.
	// This tiebreaker causes less joins to be flipped from LEFT to RIGHT
	// later by the BuildProbeSideOptimizer, and we strongly prefer LEFT
	if (new_cost == old_cost) {
		auto new_right_cardinality = right_plan->second->cardinality;
		auto existing_right = plans.find(entry->second->right_set);
		if (existing_right != plans.end()) {
			auto old_right_cardinality = existing_right->second->cardinality;
			if (new_right_cardinality > old_right_cardinality) {
				plans[new_set] = std::move(new_plan);
				return plans[new_set].get();
			}
		}
	}
```

**Flow:** strict `<` replaces unconditionally; exact `==` falls to the tiebreaker: prefer the plan whose RIGHT input has LARGER cardinality. The comment chain explains the porting trap — with LEFT joins every ordering preserves LHS cardinality so costs tie constantly, and `BuildProbeSideOptimizer` later flips some joins' sides; keeping the fatter relation on the build (right) side minimizes those flips because LEFT orientation is preferred downstream.
**Invariant:** Replacement happens ONLY on `<` or on `==` with strictly greater right cardinality (`>` not `>=`) — never on `==` with equal or smaller right side. A porter using `<=` silently destroys this probe-side preference.
**Probe:** `grep -n 'new_cost == old_cost' src/optimizer/join_order/plan_enumerator.cpp` → line 222; behavior pinned by `test/optimizer/joins/left_join_reordering/left_join_cardinality_estimation.test` and `test/optimizer/joins/wide_build_skinny_probe.test`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "EmitPair tiebreaker old_cost plans DPJoinNode", limit: 8 });
```

## Verdict
Adopt the three-branch replace rule verbatim including the comment rationale. Adapt node types to host plan representations. Omit nothing here — the rule is fully portable. Caveat: covered indirectly via left-join reordering sqllogic tests, no isolated unit test.
