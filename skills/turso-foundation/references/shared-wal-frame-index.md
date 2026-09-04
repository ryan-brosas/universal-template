<!-- capsule-v2 -->
# Shared-WAL frame index — how do you expose an append-only page→frame map through mmap without any reader seeing a half-written entry?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What publish ordering, growth policy, and rollback discipline let a shared index answer "latest frame for page P" safely across processes?

## Release-publish via len CAS; block-hashed lookup scanned newest-block-first
**Path/Symbol:** `core/storage/shared_wal_coordination.rs:2247-2328` (`record_frame`), :2334-2360 (`rollback_frames`), :2383-2430 (`find_frame`), :2438-2478 (`iter_latest_frames`); layout consts :59-70 (`FRAME_INDEX_BLOCK_CAPACITY = 4096`, `HASH_SLOTS = capacity × 2` mirroring "SQLite's oversubscription", `MAX_FRAME_INDEX_BLOCKS = 64`, lazy `INITIAL_FRAME_INDEX_BLOCKS = 1`).
**Signature:** `pub(crate) fn record_frame(&self, page_id: u64, frame_id: u64)` under `frame_index_publish_lock`; `find_frame(page_id, min_frame, max_frame, frame_watermark: Option<u64>) -> Option<u64>`.
**Data Shape:** fixed blocks of `(page_id, frame_id)` entries + per-block open-addressed u16 hash slots mapping page_id → local entry index; total published length is ONE atomic (`frame_index_len`) that IS the visibility boundary.

### Decisive source
```rust
// :2318-2327 — the publish step:
// Publish the new entry only after its payload is fully written, so
// readers that synchronize via frame_index_len never observe an
// uninitialized slot.
turso_assert!(header.frame_index_len.compare_exchange(slot, slot+1, Release, Acquire).is_ok(),
    "shared WAL frame index length changed while publishing an entry");
// :2298-2301 — structural monotonicity:
assert!(frame_id > previous.frame_id, "shared WAL frame ids must increase monotonically...");
```
Readers load `len` (min'd with capacity), then scan blocks in REVERSE so the most recent entry for a page wins; per-block hash gives O(1) within a block. Overflow is honest: when every reserved block is consumed the writer sets `frame_index_overflowed=1` and returns — readers fall back to scanning the WAL file rather than trusting a truncated view. Rollback trims entries with frame_id > target and REBUILDS each surviving block's hash (test-pinned: `rebuilds_block_hash_after_rollback`); a restart resets the whole index when frame_id==1 && max_frame==0.

**Flow:** write frame to WAL → record_frame {lock → reset-on-restart check → grow-or-overflow → monotonic assert → payload write → hash insert → len CAS} | read: snapshot len → reverse blocks → hash hit → range-check frame_id ∈ min..=max (watermark variant bounds visibility for readers pinned below the tip).
**Invariant:** len-CAS is the ONLY publication; hash tables are derived state, always rebuildable from entries; overflow must be signaled, never silently truncated.
**Probe:** in-file tests: `mapped_shared_wal_coordination_tracks_frame_index_entries`, `_grows_frame_index_across_block_boundary`, `_marks_overflow_once_reserved_space_is_full`, `_handles_hash_collisions` (deliberate colliding page-id generator), `_respects_sparse_frame_watermarks`, `_install_snapshot_trims_stale_frame_index_tail`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "record_frame find_frame frame_index_len rollback_frames", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt append-only + single-length-word publication for shared indexes; adapt block sizing/hash width to your entry rate. Omit the watermark parameter unless readers at multiple snapshots must share one index.
