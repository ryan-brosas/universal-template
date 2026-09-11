<!-- capsule-v2 -->
# SSTable exclusion watermarks — how long must a flushed generation stay readable after compaction drains it?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** When compaction has merged SSTable generations into the base table, what gates dropping them from an indexed read?

## Index-catch-up gating
**Path/Symbol:** `rust/lancedb/src/table/query/lsm.rs:exclusion_watermarks` (248–272); index resolution via `arm_maintained_index_names` (516–573) + `resolve_single_index` (583–602); snapshot assembly `snapshot_from_manifest` (340–356).
**Signature:** `fn exclusion_watermarks(details: &MemWalIndexDetails, index_names: &[String]) -> HashMap<Uuid, u64>`.
**Data Shape:** Per shard (Uuid): watermark = min(compaction generation, min over relied-on indexes of caught_up_generation_for_shard); missing catch-up entry ⇒ watermark 0 (retain everything).

### Decisive source
```rust
for name in index_names {
    match details.index_catchup.iter()
        .find(|icp| icp.index_name == *name)
        .and_then(|icp| icp.caught_up_generation_for_shard(&entry.shard_id))
    {
        Some(caught_up) => watermark = watermark.min(caught_up),
        // No entry means the index is *not* known to hold these rows,
        // and the base arm is index-only -- so every generation stays
        // readable from its SSTable.
        None => watermark = 0,
    }
}
exclude.entry(entry.shard_id).or_insert(watermark);
```

**Flow:** For each compacted SSTable entry: start at its generation, clamp down by EVERY index the query relies on's per-shard catch-up, keep first occurrence per shard. `snapshot_from_manifest` then skips SSTables with `generation <= watermark` when assembling read snapshots.
**Invariant:** The watermark is the MINIMUM across all relied-on indexes — gating on one alone drops SSTables another index has not yet re-indexed, and those rows silently vanish from that arm's results (upstream test: vec caught up @7, fts @4 ⇒ exclusion stops at 4 regardless of order). An UNTRACKED index pins the whole shard at 0 — it is never widened by a tracked sibling. Known gap (documented in source): a vector search with a scalar/bitmap prefilter is gated on its vector index alone because no Lance API exposes the planner's chosen scalar indexes.
**Probe:** `cargo test -p lancedb --lib table::query::lsm::tests::exclusion_watermark_gates_on_lagging_index_catchup` (plus sibling tests pinning minimum-across-indexes, untracked-retains-everything, and segment dedup).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "exclusion_watermarks index_catchup compacted_sstables", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt min-across-relied-indexes + missing-entry-pins-zero as the retention rule; adapt the MemWalIndexDetails plumbing to host metadata; omit the multi-index scalar-prefilter gap handling until the host has planner introspection. Direct-test coverage present (three dedicated unit tests).
