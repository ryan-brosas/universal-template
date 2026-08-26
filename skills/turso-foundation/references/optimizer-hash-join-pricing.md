<!-- capsule-v2 -->
# Hash-join access pricing — when does the planner pick a hash join over a seek?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** How is hash-join cost computed and what disqualifies a candidate join key from hash-join eligibility?

## Hash-join cost estimation + eligibility gates
**Path/Symbol:** `core/translate/optimizer/access_method.rs:estimate_hash_join_cost` (:1200, drift-shifted from :1199 at `main@d9266124f`); candidate builder emitting `AccessMethodParams::HashJoin` (:1443-1487 region); `expr_is_simple_column_from_table` (:1490-1496).
**Signature:** `pub fn estimate_hash_join_cost(build_cardinality: f64, probe_cardinality: f64, mem_budget: usize, probe_multiplier: f64, params: &CostModelParams) -> Cost`.
**Data Shape:** Produces `AccessMethod { cost, estimated_rows_per_outer_row, consumed_where_terms, params: AccessMethodParams::HashJoin { build_table_idx, probe_table_idx, join_keys, mem_budget, materialize_build_input: false, use_bloom_filter: false, join_type } }`. Budget is `DEFAULT_MEM_BUDGET` imported from `crate::vdbe::hash_table` (32KB debug / 64MB release).

### Decisive source
```rust
// core/translate/optimizer/access_method.rs
let estimated_hash_table_size =
    (build_cardinality as usize).saturating_mul(params.hash_bytes_per_row as usize);
let will_spill = estimated_hash_table_size > mem_budget;
let build_cost = build_cardinality * (params.hash_cpu_cost + params.hash_insert_cost);
// If the hash-join probe loop is nested under prior tables, the probe
// scan repeats per outer row, so scale by probe_multiplier.
let probe_cost = probe_cardinality * (params.hash_cpu_cost + params.hash_lookup_cost)
                 * probe_multiplier;
// Grace hash join writes partitions and reads them back: 2x page IO
let spill_cost = if will_spill {
    let build_pages = (build_cardinality / params.rows_per_table_page).ceil();
    let probe_pages = (probe_cardinality / rows_per_table_page).ceil();
    (build_pages + probe_pages) * 2.0 * probe_multiplier
} else { 0.0 };
```
Eligibility (preceding block): for each join key, if either side's expression is a simple column/rowid of its table AND that column is a rowid alias OR covered by any index on that table → `return None` (an index seek replaces the hash join). Output cardinality per build row = `probe_cardinality × Π join-key selectivity`; LeftOuter clamps to ≥1; FullOuter additionally maxes with `probe/build`.

**Flow:** enumerate join keys from usable constraints → reject seek-covered keys → price via estimate_hash_join_cost at DEFAULT_MEM_BUDGET → register AccessMethod into the shared arena (truncated by the DP on rejection — see optimizer-join-order-dp).
**Invariant:** The planner's spill model must mirror the executor's real budget constant (both import `DEFAULT_MEM_BUDGET` from vdbe/hash_table); diverging copies silently flip spill-vs-memory plans. Bloom filter and materialized-build flags are emitted FALSE here — runtime emission decides later.
**Probe:** text anchors: `grep -c 'DEFAULT_MEM_BUDGET,' core/translate/optimizer/access_method.rs` → 2 (cost + params). Executor twin tests: `core/vdbe/hash_table.rs::test_adaptive_partition_count_bounds` (:3659 asserts power-of-two count within MIN=16..MAX=128 after forced spill).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "estimate_hash_join_cost HashJoinType FullOuter", limit: 10 });
```

## Verdict
Adopt the cost formula (build+probe CPU, grace-spill 2×page-IO × probe_multiplier) and the seek-replacement eligibility rule; adapt mem-budget plumbing if the host makes it configurable (upstream TODO: PRAGMA); omit the FULL-OUTER chaining restrictions already covered by optimizer-join-order-dp.
