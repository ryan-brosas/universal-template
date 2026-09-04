<!-- capsule-v2 -->
# dphyp-pair-budget-approximate-fallback — When does exact DPhyp join enumeration give up, and what guarantees a valid plan still comes out?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does the join-order optimizer bound worst-case enumeration time without ever failing a query?

## Connected graph-selected seam
**Path/Symbol:** `src/optimizer/join_order/plan_enumerator.cpp:TryEmitPair` (:237-251), `SolveJoinOrder` (:568-616), `SolveJoinOrderApproximately` (:408-507), `HasCompletePlan` (:509-516).
**Signature:** `bool TryEmitPair(JoinRelationSet &left, JoinRelationSet &right, const vector<reference<NeighborInfo>> &info)`; `bool SolveJoinOrder()`.
**Data Shape:** `pairs` is a plain member counter incremented on every candidate pair emission. Settings: `ApproximateJoinOrderThresholdSetting` ("approximate_join_order_threshold") and `DebugForceNoCrossProductSetting`. `plans` is a `reference_map_t<JoinRelationSet, unique_ptr<DPJoinNode>>` DP table keyed by interned relation sets (unique object identity guaranteed by `JoinRelationSetManager::GetJoinRelation`).

### Decisive source
```cpp
	if (pairs >= 10000) {
		// when the amount of pairs gets too large we exit the dynamic programming and resort to a greedy algorithm
		// FIXME: simple heuristic currently
		// at 10K pairs stop searching exactly and switch to heuristic
		return false;
	}
```
and the dispatch ladder:
```cpp
	if (query_graph_manager.relation_manager.NumRelations() >= swap_to_approximate_threshold) {
		solved = SolveJoinOrderApproximately();
	} else {
		auto completed_exactly = SolveJoinOrderExactly();
		if (completed_exactly && !HasCompletePlan() && ActivateRequiredCrossProducts()) {
			completed_exactly = SolveJoinOrderExactly();
		}
		if (!completed_exactly || !HasCompletePlan()) {
			// Exact enumeration either reached its pair budget or could not connect the graph.
			solved = SolveJoinOrderApproximately();
		} else {
			solved = true;
		}
	}
```

**Flow:** relations ≥ threshold → greedy immediately. Below threshold → exact DPhyp (`EmitCSG`/`EnumerateCSGRecursive`/`EnumerateCmpRecursive`, Moerkotte & Neumann "Dynamic Programming Strikes Back"); any `TryEmitPair` returning false aborts exact search mid-flight; if no full plan exists, cross-product edges are activated ONCE and exact search reruns from scratch; still no full plan → greedy O(r³) smallest-cost pairing over the surviving DP table. Greedy itself can fail only if the graph is truly disconnected AND cross products are forbidden — then `SolveJoinOrder` returns false and `JoinOrderOptimizer::Optimize` falls back to the ORIGINAL input tree (`join_order_optimizer.cpp:96-100`: "The original tree is still intact and is always a valid fallback"). A `false` return is NOT an error — reconstruction of the untouched plan is the defined success path.
**Invariant:** The pair budget aborts enumeration, never correctness: every bail-out path terminates in either a complete plan, the greedy result, or the original plan. `ActivateRequiredCrossProducts` may flip the latch only once (`required_cross_products_activated`) so retry storms are impossible.
**Probe:** `grep -n 'pairs >= 10000' src/optimizer/join_order/plan_enumerator.cpp` → line 243; behavior pinned by `test/optimizer/joins/required_cross_product_activation.test` (foreach threshold 0 30 — same query must succeed under both exact and approximate modes) and `test/optimizer/joins/order_optimizer_bindings.test` ("In the join order optimizer queries need to have the correct bindings").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "TryEmitPair SolveJoinOrderExactly pairs budget", limit: 10 });
```

## Verdict
Adopt the three-ladder structure (exact → single cross-product re-run → greedy → original-plan fallback) and the 10k pair budget as portable contract. Adapt the concrete budget value and threshold setting name to host config. Omit the DEBUG subset-count asserts. Caveat: no unit test isolates TryEmitPair's counter directly; behavior is covered end-to-end by sqllogic tests under both thresholds.
