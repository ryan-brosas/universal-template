<!-- capsule-v2 -->
# Optimize action fan-out — what does All actually run, in what order, and what is forbidden on a checked-out table?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** How do compact / prune / index-optimize compose into one optimize call, and what are their ordering and mutability contracts?

## execute_optimize
**Path/Symbol:** `rust/lancedb/src/table/optimize.rs:execute_optimize` (163–213), `OptimizeAction` enum (30–90), `optimize_indices` (105–112), `cleanup_old_versions` (129–140).
**Signature:** `pub(crate) async fn execute_optimize(table: &NativeTable, action: OptimizeAction) -> Result<OptimizeStats>`; enum variants `All | Compact{options, remap_options} | Prune{older_than, delete_unverified, error_if_tagged_old_versions} | Index(OptimizeOptions)`.
**Data Shape:** Returns OptimizeStats { compaction: Option<CompactionMetrics>, prune: Option<RemovalStats> } — each action fills ONLY its own stat (All fills both).

### Decisive source
```rust
OptimizeAction::All => {
    // Call helper functions directly to avoid async recursion issues
    stats.compaction = Some(compact_files_impl(table, CompactionOptions::default(), None).await?);
    stats.prune = Some(cleanup_old_versions(table,
        Duration::try_days(7).expect("valid delta"), None, None).await?);
    optimize_indices(table, &OptimizeOptions::default()).await?;
}
```

**Flow:** All = Compact(7-day prune default) → Prune(default keep 7 days, delete_unverified=None) → Index-optimize, IN THAT ORDER. Compaction merges small fragments to `target_rows_per_fragment`; prune deletes old dataset versions older_than the cutoff (files newer than 7 days never deleted unless `delete_unverified=true`, documented corruption risk if concurrent writers exist; tagged old versions can hard-error); index optimization adds unindexed rows into EXISTING index partitions without retraining (assigns new data to existing clusters — never moves clusters). Every entry calls `dataset.ensure_mutable()` first: a checked-out (time-travel) handle fails ALL four actions with "cannot be modified when a specific version is checked out".
**Invariant:** Order matters operationally: compact first so index-optimization covers post-compaction fragments; prune AFTER compact so superseded versions are reclaimable. Index optimize ≠ rebuild — accuracy drifts over massive appends because the model (clusters) is frozen; docs say users should occasionally retrain. `defer_index_remap` exists on CompactionOptions to defer index remapping after row-id rewrites.
**Probe:** `cargo test -p lancedb --lib table::optimize::tests::test_optimize_all` (pins both stats populated + data integrity; `test_optimize_fails_on_checked_out_table` pins all-four-variants mutability gate).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "execute_optimize OptimizeAction compact_files cleanup_old_versions optimize_indices", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered All pipeline and per-action stat isolation; adapt retention defaults (7d) to host policy; omit remap-options passthrough if the host has no index remapper. Direct-test coverage present (rstest covers all four actions against checkout failure).
