<!-- capsule-v2 -->
# Optimizer join-order DP — how does Turso enumerate join orders without exploding?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** What is the exact search strategy, pruning rule, and outer-join legality machinery a porter must reproduce to get identical join orders?

## Join-order enumeration kernel
**Path/Symbol:** `core/translate/optimizer/join.rs:compute_best_join_order_with_context` (:1089-1565); threshold const :1569 (drift-shifted from :1568 at `main@d9266124f`, value unchanged = 12, used at :1118); greedy fallback :1578-1767; naive plan + memo :1206-1258.
**Signature:** `pub(crate) fn compute_best_join_order_with_context<'a>(joined_tables: &[JoinedTable], initial_input_cardinality: f64, planning_context: JoinPlanningContext<'_>, constraints: &'a [TableConstraints], base_table_rows: &[RowCountEstimate], access_methods_arena: &'a mut Vec<AccessMethod>, where_clause: &mut [WhereTerm], subqueries: &[NonFromClauseSubquery], index_method_candidates: &[IndexMethodCandidate], params: &CostModelParams, analyze_stats: &AnalyzeStats, available_indexes: &AvailableIndexes, table_references: &TableReferences, schema: &Schema) -> Result<Option<BestJoinOrderResult>>`.
**Data Shape:** `BestJoinOrderResult { best_plan: JoinN, best_ordered_plan: Option<JoinN> }`. Memo is `HashMap<TableMask, HashMap<usize, JoinN>>` keyed by subset mask THEN last-table index — deliberately MULTIPLE plans per subset ("cheapest subset plan is not always the best foundation for the next join", e.g. hash-join chaining). Pre-sized to `2usize.pow(n-1)`.

### Decisive source
```rust
// core/translate/optimizer/join.rs
let num_tables = joined_tables.len();
// For large queries, use greedy join ordering instead of exhaustive DP.
// The DP algorithm has O(2^n) complexity which becomes prohibitively slow
// beyond ~12 tables. The greedy algorithm is O(n²) ...
if num_tables > GREEDY_JOIN_THRESHOLD {   // pub const GREEDY_JOIN_THRESHOLD: usize = 12;
    return compute_greedy_join_order(...);
}
let naive_plan = compute_naive_left_deep_plan(...)?;      // pruning threshold seed
let mut cost_upper_bound = best_plan.as_ref().map_or(Cost(f64::MAX), |plan| plan.cost);
```

**Flow:** (1) empty input → `Ok(None)`; >12 tables → greedy (`find_best_starting_table` then repeatedly pick lowest-marginal-cost connected table, honoring left-join dep masks). (2) Else compute naive left-deep plan as the pruning threshold `cost_upper_bound` (also clamped by `planning_context.cost_limit`). (3) Base case: every single table via `join_lhs_and_rhs(None, ...)`. (4) Build legality maps when any `join_info.is_ordering_constrained()` or FULL OUTER exists: `left_join_illegal_map: rhs→mask(lhs-forbidden)` and `required_lhs_by_table[j]`; FULL OUTER adds a reordering barrier in BOTH directions so later inner tables cannot float before it (NULL-leak comment :1300-1307). (5) For each subset mask of size 2..n that satisfies all `required_lhs`: for each rhs in mask, take lhs variants from memo, rebuild `join_order`, call `join_lhs_and_rhs`, keep per-(mask,last) best AND per-mask `best_ordered_for_mask` (order-satisfying plans may exceed `cost_upper_bound` yet win later by eliminating a sort). (6) Arena discipline: before each candidate call record `arena_len = access_methods_arena.len()`; on reject/replacement `access_methods_arena.truncate(arena_len)` — rejected access methods must not leak into the arena indexes stored in surviving plans. (7) Full-mask winners update `best_plan`; return `best_ordered_plan: None` if best is itself ordered.
**Invariant:** Inner-join commutativity/associativity justifies dropping dominated subsets — but ONLY when no ordering-constrained join exists; any port that reorders LEFT/SEMI/ANTI/FULL OUTER by cost alone produces wrong results (NULL-filled probe rows leaking past an inner join). Plans worse than `cost_upper_bound` survive only through the order-target escape hatch.
**Probe:** `core/translate/optimizer/join.rs::test_compute_best_join_order_empty` (:2528 asserts `result.is_none()` with zero tables) and `test_compute_best_join_order_star_schema` (:3197 — 9 dim tables + fact; asserts fact table chosen OUTER because dims become rowid seeks, each dim access method has exactly 1 eq constraint whose lhs_mask contains FACT_TABLE_IDX). Text anchors: `grep -c 'GREEDY_JOIN_THRESHOLD: usize = 12' core/translate/optimizer/join.rs` → 1; `grep -c 'FULL OUTER JOIN chaining is not yet supported' core/translate/optimizer/join.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "compute_best_join_order_with_context compute_greedy_join_order", limit: 10 });
```
(resolves `turso.core.translate.optimizer.join.compute_best_join_order` :1051-1083 and `compute_greedy_join_order` :1578-1767 line-exact)

## Verdict
Adopt the three-tier search (naive-thresholded Selinger DP ≤12 tables / greedy beyond), multi-variant memo keyed (mask,last), outer-join legality masks, and arena truncation discipline. Adapt `CostModelParams` thresholds and error strings. Omit TLA+/antithesis harnesses under `tlaplus/` and `scripts/antithesis/`.
