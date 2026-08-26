<!-- capsule-v2 -->
# LSM merge_insert dispatch + single-shard rule — which upserts go through the ShardWriter and what makes a call atomic?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** How does `merge_insert` decide between the standard merge path and the MemWAL shard writer, and what does "one call = one shard" mean mechanically?

## Dispatch decision + shard validation
**Path/Symbol:** `rust/lancedb/src/table/merge/lsm.rs:lsm_dispatch_decision` (552–607), `execute_lsm_merge_insert` (666–711), `resolve_input_shard`/`resolve_batch_shard` (714–806), `align_batch_schema` (962–989).
**Signature:** `pub(crate) async fn lsm_dispatch_decision(table: &NativeTable, params: &MergeInsertBuilder) -> Result<LsmDispatch>`; `async fn execute_lsm_merge_insert(table: &NativeTable, plan: LsmPlan, validate_single_shard: bool, new_data: Box<dyn RecordBatchReader + Send>) -> Result<MergeResult>`.
**Data Shape:** Dispatch: `params.use_lsm: Option<bool>` × installed spec; requires upsert-only builder shape (`when_matched_update_all && no filt && when_not_matched_insert_all && !by_source_delete`). Sharding modes: Bucket{num_buckets} / Identity / Unsharded. MergeResult from LSM path reports ONLY `num_rows` (insert/update split unknown until compaction).

### Decisive source
```rust
if !is_upsert_only(params) {
    return Err(Error::InvalidInput {
        message: "merge_insert: when an LSM write spec is set, only the upsert form \
            (when_matched_update_all without a filter + when_not_matched_insert_all, \
             no by-source delete) is supported; call use_lsm(false) ...".to_string() });
}
// execute:
let mut batches: Vec<RecordBatch> = Vec::new();
for batch in new_data { /* align schema, skip empties, count rows */ }
let Some(shard_id) = resolve_input_shard(&plan.mode, dataset.schema(), &batches,
                                          validate_single_shard)? else {
    return Ok(lsm_merge_result(0));      // empty input: nothing written
};
let writer = table.dataset.shard_writer().writer_for_shard(dataset.as_ref(), shard_id, config).await?;
writer.put(batches).await?;              // ONE atomic put of the whole batch vector
```

**Flow:** (1) Explicit `use_lsm==Some(false)` short-circuits to Standard; (2) no spec + `Some(true)` = error; no spec + unset = Standard; (3) `on` columns must equal the table's unenforced PK (or be empty = default to PK); (4) upsert-only shape enforced; (5) mode resolved from stored sharding transform names `"bucket"`/`"identity"`/`"unsharded"`. Execution collects + schema-aligns + shard-validates the ENTIRE input before any write — `ShardWriter::put` is atomic over the batch vector, so validation failure leaves the MemWAL untouched. Shard ids are deterministic UUIDv5 under a hardcoded namespace: `bucket-{n}`, `identity-{le-bytes|utf8}` (null identity values are REJECTED), `unsharded`. One writer per session: opening for a different shard errors until `close_lsm_writers()` drains the cache.
**Invariant:** `validate_single_shard=false` checks ONLY THE FIRST ROW of the whole input — mixed-bucket inputs then silently route by row 0 (documented, tested behavior, not an accident). Bucket evaluator returns Int32 buckets; null routing values hash to bucket 0. Input batches must carry the exact dataset schema INCLUDING field metadata — `align_batch_schema` rewraps by column NAME (order irrelevant) and rejects dtype mismatches.
**Probe:** `cargo test -p lancedb --lib table::merge::lsm::tests` (pins bucket assignments `[1,5,0]` for `[a,b,None]`@8 buckets, mixed-shard rejection vs first-row acceptance, deterministic distinct shard ids, schema reorder alignment).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "lsm_dispatch_decision execute_lsm_merge_insert resolve_batch_shard", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dispatch truth table, collect-validate-then-single-atomic-put execution shape, and uuidv5 shard derivation; adapt sharding transforms to host partitioners; omit the writer-config defaults ladder if the host has no tunable writer. Direct-test coverage present (12 unit tests in-module).
