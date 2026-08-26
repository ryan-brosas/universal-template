<!-- capsule-v2 -->
# required-cross-product-activation-latch — When are optimizer-forbidden cross products legalized, and only once?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does enumeration connect a predicate graph whose syntactic cross products were initially refused as join-order candidates?

## Connected graph-selected seam
**Path/Symbol:** `src/optimizer/join_order/query_graph_manager.cpp:ActivateRequiredCrossProducts` (:895-933); consumer `src/optimizer/join_order/plan_enumerator.cpp:ActivateRequiredCrossProducts` (:518-526) and `SolveJoinOrder` (:579).
**Signature:** `bool QueryGraphManager::ActivateRequiredCrossProducts()`; enumerator wrapper resets `pairs = 0` and clears both caches.
**Data Shape:** `required_cross_products_activated` bool latch; `join_operators` stored in POSTORDER; per-operator `left_relations`/`right_relations` sets; union-find style `FindGraphComponent`.

### Decisive source
```cpp
	if (required_cross_products_activated || Settings::Get<DebugForceNoCrossProductSetting>(context)) {
		return false;
	}
	required_cross_products_activated = true;

	bool added_edge = false;
	// Operators are stored in postorder. Required child cross products therefore connect each input scope before its
	// parent is considered.
	for (auto &operator_ptr : join_operators) {
		auto &op = *operator_ptr;
		if (op.type != JoinOrderOperatorType::CROSS_PRODUCT) {
			continue;
		}
```
and the enumerator side:
```cpp
bool PlanEnumerator::ActivateRequiredCrossProducts() {
	if (!query_graph_manager.ActivateRequiredCrossProducts()) {
		return false;
	}
	pairs = 0;
	connection_cache.clear();
	neighbor_set_cache.clear();
	return true;
}
```

**Flow:** exact enumeration completes but `HasCompletePlan()` is false → the graph is disconnected under predicate edges alone. The manager walks syntactic CROSS_PRODUCT operators in postorder, keeps only those whose left/right inputs belong to DIFFERENT connected components (`FindGraphComponent` comparison), materializes bidirectional empty-filter edges for every relation pair across the split, and unions the components. Enumerator resets its pair budget and invalidates both memo caches because `GetConnections` results are now stale. A second exact run then succeeds. Redundant cross products (both sides already same component) are skipped — activating everything would explode enumeration.
**Invariant:** The latch makes activation idempotent AND one-shot: `IsJoinOrderCandidate` consults `CanCreateCrossProduct`, so before activation no candidate may introduce a cross product; after, they're legal only where needed. Optimizer-introduced cross products remain invalid outside inner-join companion sets (see greedy fallback comment, plan_enumerator.cpp:457).
**Probe:** `grep -n 'Activate explicit cross products only when they are needed' test/optimizer/joins/required_cross_product_activation.test` → line 2; test drives foreach threshold 0 30 proving identical results through both ladders.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "ActivateRequiredCrossProducts FindGraphComponent CreateEdge", limit: 8 });
```

## Verdict
Adopt: postorder component-connecting pass, bidirectional edge creation, cache+budget reset on activation, single-shot latch. Adapt to host operator representation. Omit debug force-no-cross-product PRAGMA plumbing unless porting the debug surface. Caveat: dedicated sqllogic test exists; no C++ unit test isolates the manager function.
