<!-- capsule-v2 -->
# ShardWriterCache read snapshot — in what order are memtables and manifest captured, and why does the order matter?

**Source:** LanceDB Apache-2.0 `main@1b950188`; Codebase Memory `ext-lancedb`. **Question:** How does the read path get a consistent view of this session's in-flight writes without locking the writer?

## Capture-order invariant
**Path/Symbol:** `rust/lancedb/src/table/merge/lsm.rs:ShardWriterCache` (349–502), specifically `read_snapshot` (468–491) and `writer_for_shard` (430–461).
**Signature:** `pub(crate) async fn read_snapshot(&self) -> Result<Option<(Uuid, Option<ShardManifest>, Option<InMemoryMemTables>)>>`; `async fn writer_for_shard(&self, dataset: &Dataset, shard_id: Uuid, config: ShardWriterConfig) -> Result<Arc<ShardWriterEntry>>`.
**Data Shape:** Single slot `RwLock<Option<(Uuid, Arc<ShardWriterEntry>)>>` — one cached writer per table/session. Entry wraps `RwLock<Option<ShardWriter>>` (`None` = closed). Snapshot triple: (shard id, authoritative in-memory manifest, active+frozen memtable refs).

### Decisive source
```rust
// Capture memtables before the manifest. If a flush interleaves, dedup
// tolerates the same rows appearing in both a memtable and a freshly
// flushed generation, but would drop rows present in neither. Manifest
// last guarantees any generation flushed mid-capture is still covered.
let memtables = entry.in_memory_memtable_refs().await?;
let manifest = entry.manifest().await?;
Ok(Some((shard_id, manifest, memtables)))
```

**Flow:** (1) Copy the slot under a short read lock (clone the Arc, drop the guard — long ops never hold the lock); (2) capture memtable refs FIRST, manifest SECOND; (3) the LSM read path overrides the on-disk manifest view for THIS shard with the captured snapshot, so reads see not-yet-flushed writes. Double-checked locking in `writer_for_shard`: read-guard fast path, then re-check under write guard before opening. `check_shard_match` errors when the cached writer belongs to a different shard. WAL-only writers (`enable_memtable=false`) have no memtables and `in_memory_memtable_refs` errors in that mode — the read path skips them entirely (on-disk manifests already cover their SSTables).
**Invariant:** MEMTABLES-BEFORE-MANIFEST is load-bearing: dedup tolerates duplicates across tiers but NOT gaps; reversed capture loses rows that drain from memtable→flush between the two captures. A porter who "fixes" the order or holds one big lock breaks concurrent writers or loses rows.
**Probe:** `cargo test -p lancedb --lib table::merge::lsm::tests::shard_ids_are_deterministic_and_distinct` (cache mechanics) — the capture-order property itself is documented in-source and exercised by the LSM read tests; treat as prose-pinned if running only unit tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-lancedb", query: "ShardWriterCache read_snapshot writer_for_shard drain_and_close", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capture ordering and the clone-slot-release-lock pattern; adapt RwLock<Option<..>> writer lifecycle to host concurrency primitives; omit WAL-only-mode special-casing only if the host lacks that configuration. Coverage caveat: ordering invariant documented in decisive comments rather than a dedicated unit test.
