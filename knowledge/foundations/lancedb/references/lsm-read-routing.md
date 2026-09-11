<!-- capsule-v2 -->
# MemWAL LSM read routing + shape rejection — when do reads leave the base table, and which query shapes must fail loudly?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** How is a query routed to the LSM scanner, and why are unsupported shapes hard errors instead of silent base-table fallbacks?

## Routing ladder
**Path/Symbol:** `rust/lancedb/src/table/query.rs:create_plan` (131–164) → `rust/lancedb/src/table/query/lsm.rs:create_lsm_plan` (59–134) with `reject_unsupported` (145–214).
**Signature:** `pub async fn create_plan(table: &NativeTable, query: &AnyQuery, options: QueryExecutionOptions) -> Result<Arc<dyn ExecutionPlan>>`.
**Data Shape:** Routing input: `query.base.use_lsm: Option<bool>` × table state `has_spec = mem_wal_index_details().is_some()`. Output: either an LsmScanner plan over base ∪ SSTables ∪ in-memory memtables, or the standard Lance Scanner plan.

### Decisive source
```rust
let use_lsm = match query.base.use_lsm {
    Some(true) if !has_spec => return Err(Error::InvalidInput {
        message: "use_lsm(true) was set but the table has no MemWAL write spec; \
            install one with set_lsm_write_spec or leave use_lsm unset".to_string() }),
    Some(enable) => enable,
    None => has_spec,          // <-- AUTO-ROUTE: unset means "LSM iff a spec exists"
};
if use_lsm { return lsm::create_lsm_plan(table, ds_ref, query).await; }
```
and the rejection contract:
```
unsupported shapes => Error::NotSupported{ "... set use_lsm(false) to read the base table only" }
  multiple query vectors | hybrid (vector+FTS) | reranker | order_by
  with_row_id ("the LSM scanner exposes _rowaddr, not a stable _rowid")
  distance_range / use_index(false) on vector search   // change RESULTS, not just recall
  postfilter on vector or FTS ("the LSM scanner always prefilters")
  Select::Dynamic / Select::Expr | Substrait filters | take by _rowid/_rowoffset
  time-traveled (checked-out) dataset handle           // WAL exposes CURRENT live state
```

**Flow:** (1) `check_filter` first; (2) resolve routing per the match above; (3) LSM path rejects unsupported shapes BEFORE building context; note the deliberate asymmetry — recall knobs (`ef`, `approx_mode`, `maximum_nprobes`) are left to no-op because they don't change results, while `distance_range` and brute-force `use_index(false)` ARE rejected since they would silently alter results. A `where` filter is never rejected: all three arms (plain/FTS/vector) terminate on the same `LsmScanner`, which threads it as a prefilter uniformly.
**Invariant:** On a MemWAL table, an unsupported shape must ERROR, not fall back — a base-only fallback silently excludes un-compacted data (the doc comment calls this out explicitly). A porter who converts these errors into fallbacks ships a correctness bug disguised as graceful degradation.
**Probe:** `cargo test -p lancedb --lib table::query::lsm::tests` plus plan-level assertions in `rust/lancedb/src/table/query.rs` tests (`test_fast_search_plan`, pagination tests) for the non-LSM arm.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "create_plan use_lsm mem_wal routing reject_unsupported", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the tri-state routing match and the fail-don't-fallback rejection policy verbatim; adapt the rejected-shape list to whichever query knobs the host planner supports; omit namespace-pushdown interplay only if the host has no remote execution path. Coverage caveat: routing pinned by unit tests around `use_lsm` semantics; full LSM integration requires the lance MemWAL feature.
