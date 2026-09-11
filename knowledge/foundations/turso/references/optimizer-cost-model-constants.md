<!-- capsule-v2 -->
# Cost model constants — what numbers drive Turso's scan/seek/hash-join pricing?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** Which default parameters, selectivity ladders, and ANALYZE rules must a porter copy for plan parity?

## Cost model + cardinality estimation
**Path/Symbol:** `core/translate/optimizer/cost_params.rs:CostModelParams::new` (:103-140); `core/translate/optimizer/cost.rs:estimate_index_cost` (:171+, drift-shifted from :166 at `main@d9266124f`), `estimate_rows_per_seek` (:285, was :283), `estimate_rows_from_analyze_stats` (:349, was :332).
**Signature:** `pub fn estimate_cost_for_scan_or_seek(index_info: Option<IndexInfo>, constraints: &[Constraint], usable_constraint_refs: &[RangeConstraintRef], input_cardinality: f64, base_row_count: RowCountEstimate, is_index_ordered: bool, params: &CostModelParams, analyze_ctx: Option<&AnalyzeCtx>) -> Cost`.
**Data Shape:** `Cost(pub f64)`; `RowCountEstimate::{HardcodedFallback, AnalyzeStats}` deref to f64 (fallback = `rows_per_table_fallback` 1,000,000). `IndexInfo { unique, column_count, covering, rows_per_leaf_page }`.

### Decisive source
```rust
// cost_params.rs — the defaults a port must match
rows_per_table_fallback: 1_000_000.0,
rows_per_table_page: 50.0,
sel_eq_unindexed: 0.1, sel_eq_indexed: 0.001,
sel_range: 0.4, sel_is_null: 0.1, sel_is_not_null: 0.9,
sel_like: 0.2, sel_not_like: 0.2, sel_other: 0.9,
in_subquery_rows: 25.0,          // Matches SQLite's estimate (where.c line 3230)
cache_reuse_factor: 0.2, cpu_cost_per_row: 0.003, cpu_cost_per_where_step: 0.003,
cpu_cost_per_seek: 0.01, index_bonus: 0.5, sort_cpu_per_row: 0.002,
hash_cpu_cost: 0.001, hash_insert_cost: 0.002, hash_lookup_cost: 0.003,
hash_bytes_per_row: 100.0,
closed_range_selectivity_factor: 0.2,
```
```rust
// cost.rs — ANALYZE prefix rule: equality-only prefixes consume stat positions
let eq_prefix_len = constraint_refs.iter().take_while(|c| c.eq.is_some()).count();
// NULL-matching keys pile into one bucket -> decline stats, use heuristics
if constraint_refs[..eq_prefix_len].iter().any(|c| c.eq.as_ref().is_some_and(|eq| eq.null_matching)) {
    return None;
}
// trailing range bounds multiply on top of the eq-prefix rows (~whereRangeAdjust)
```

**Flow:** unique point lookup (`unique && eq_count >= column_count`, counting ONLY non-null-matching equalities) short-circuits to rows_per_seek=1. Otherwise rows/seek = ANALYZE `avg_rows_per_distinct_prefix[eq_prefix_len-1]` × range-selectivity product, falling back to per-constraint selectivity product × base rows (floor 1.0). Index cost = seeks × btree depth + leaf-page scans (point lookups get leaf cost 0 — leaf page already counted in seek) + non-covering table lookups (`input_cardinality × selectivity × table_pages`), minus `index_bonus`, floored at 0.001. Repeated scans (nested-loop inner) get `(n-1) × cache_reuse_factor` discount. Non-covering unordered full index scan doubles its own cost.
**Invariant:** B-tree depth estimate uses ln(rows)/ln(rows_per_page) CEIL — not log2; IS-equality never consumes an ANALYZE prefix position and pure-range scans decline stats entirely. A porter who feeds NULL-matching prefixes into stat lookups misprices `deleted_at IS NULL` workloads by orders of magnitude.
**Probe:** `core/translate/optimizer/join.rs::automatic_index_puts_equalities_before_ranges` (:2305). Text anchors: `grep -c 'rows_per_table_fallback: 1_000_000.0' core/translate/optimizer/cost_params.rs` → 1; `grep -c 'eq_prefix_len = constraint_refs' core/translate/optimizer/cost.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "estimate_cost_for_scan_or_seek estimate_hash_join_cost", limit: 10 });
```

## Verdict
Adopt the constant table verbatim and the eq-prefix/NULL-decline ANALYZE ladder; adapt JSON tuning (`TURSO_OPTIMIZER_PARAMS`, `optimizer_params` feature) to host config conventions; omit TPC-H-specific tuning history.
