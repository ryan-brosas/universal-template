<!-- capsule-v2 -->
# Cheapest-path visitor — DFS with cost table + dead-ends prefix tree

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How does the engine enumerate all paths of an exact total cost from START to END without exponential blowup, and what must a porter preserve when a visited path mutates the cache mid-traversal?

## PathVisitor over precomputed costs
**Path/Symbol:** `crates/milli/src/search/new/ranking_rule_graph/cheapest_paths.rs:PathVisitor` (:94-126), `VisitorState::visit_node` (:133-183), `visit_condition` (:228-281), `find_all_costs_to_end` (:285-310), `update_all_costs_before_node` (:312-343), `traverse_breadth_first_backward` (:349-403); `dead_ends_cache.rs:DeadEndsCache` (:6-100).
**Signature:** `pub fn visit_paths(mut self, visit: VisitFn<'_, G>) -> Result<()>` where VisitFn = `&mut dyn FnMut(&[Interned<Condition>], &mut RankingRuleGraph<G>, &mut DeadEndsCache<Condition>) -> Result<ControlFlow<()>>`
**Data Shape:** `all_costs_from_node: MappedInterner<QueryNode, Vec<u64>>` (sorted, deduped achievable totals); DeadEndsCache is a hand-rolled trie: node = `{ conditions: Vec<Interned<T>>, next: Vec<Self>, forbidden: SmallBitmap<T> }`.

### Decisive source
```rust
// cheapest_paths.rs module doc: "The list of all possible costs to go from any
// node to the END node is precomputed; The DeadEndsCache reduces the number of
// valid paths drastically ... In practically all cases, we avoid the exponential
// complexity that is inherent to depth-first search."
// After ANY valid path was found the cache may have changed:
if next_any_valid {
    self.forbidden_conditions = ctx.dead_ends_cache
        .forbidden_conditions_for_all_prefixes_up_to(self.path.iter().copied());
    if self.visited_conditions.intersects(&self.forbidden_conditions) {
        return Ok(ControlFlow::Continue(true));
    }
}
```

**Flow:** Prune at every step by checking remaining_cost against edge cost and membership of dest's cost table; unconditional skip-edges only check the cost table. On reaching END, call `visit` with the path — the caller may insert new forbidden entries (e.g. condition C resolved to ∅). The visitor then recomputes forbidden conditions along its OWN traversed prefix and bails out of prefixes now poisoned. Cost tables are repaired after pruning via update_all_costs_before_node (single-source) or full find_all_costs_to_end recomputation (>1 source), using a backward BFS that only visits nodes whose successors are all visited/unreachable.
**Invariant:** (1) The cost table makes "is there any completion within budget?" O(len) instead of a subtree walk; (2) dead-end knowledge is PREFIX-SCOPED — forbidding C unconditionally would wrongly kill independent paths that reach C through different ancestors; forbid_condition_after_prefix stores it under the exact traversed chain; (3) after a valid path mutates the trie, backtracking must re-derive forbidden sets from the current path prefix, or the DFS keeps exploring provably-dead branches.
**Probe:** `crates/milli/src/search/new/tests/cutoff.rs` pins the degraded/deadline behavior of this machinery end-to-end (`basic_degraded_search` :62-75 asserts result.degraded under a tiny budget; `degraded_search_cannot_skip_filter` :77-91). GREEN at HEAD (3 passed, 1 ignored).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "DeadEndsCache", limit: 5 });
```

## Verdict
Adopt the two-pruning-structure pattern (cost feasibility + prefix-scoped dead ends) for ANY cheapest-path enumeration; adapt the trie to host collections; omit SmallBitmap specifics. Behavior boundary: deadline exhaustion yields degraded results, never wrong-order results.
