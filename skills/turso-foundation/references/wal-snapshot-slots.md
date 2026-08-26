<!-- capsule-v2 -->
# WAL snapshot read-mark slots — how do readers, writers, and the checkpointer coordinate through data instead of conversations?

**Source:** turso (Turso) MIT `main@def9a0601b8ead82675e672e1843447251b15fb4`; Codebase Memory `turso`. **Question:** How are snapshot bounds encoded so a checkpointer can compute exactly how far it may backfill?

## Five slots, slot 0 fast path, CAS claim, BusySnapshot upgrade error
**Path/Symbol:** `struct WalSnapshot` `core/storage/wal.rs:192` {max_frame, nbackfills, last_checksum, checkpoint_seq, transaction_count}; lock word packing writer|31 readers|32-bit value in one u64 "updated atomically together while sitting in a single cpu cache line" (:264); slot machinery ports SQLite's wal.c commentary verbatim — READ_LOCK(0) holders "always ignore the entire WAL" (:2761); slot claim + RE-validate after locking (:997-1055); contention ladder (:3355-3395); BusySnapshot (:3398-3407); savepoint restore asserts generation match (:4520-4555); MVCC bridge `min_pinned_read_frame` (:566/:776/:876).
**Data Shape:** Readers take WalSnapshot; if fully backfilled (max_frame==nbackfills) they take SLOT 0 and ignore the WAL entirely (steady-state fast path that also lets RESTART proceed once readers drain); otherwise exclusive-CAS one of slots 1-4 to their max_frame.

### Decisive source
```rust
** WAL_READ_LOCK(0) always ignore the entire WAL and read all content
```
(wal.rs:2761, porting SQLite's own comment verbatim; companion rule :563/:1163 `determine_max_safe_checkpoint_frame`: "A checkpoint must never overwrite a page in the main DB file if some active reader might still need to read that page from the WAL" — the checkpointer only lowers FREE slots' values)

**Flow:** begin → snapshot → claim slot by CAS to max_frame → LOCK → RE-validate snapshot (retry on drift) → read via WAL or DB file → release. Contention mirrors SQLite: yields for retries 6-9, quadratic backoff `(cnt−9)² × 39µs` after, hard failure at 100. Read→write upgrade with a stale snapshot returns **BusySnapshot**, NOT Busy — "Retrying with busy_timeout will NEVER HELP" (:3398-3407). Savepoint rollback restores (frame, checksum, checkpoint_seq) captured in RollbackTo and ASSERTS generation match; no cross-checkpoint clamping is needed because positions are only captured under the held write lock.
**Invariant:** The checkpointer may transfer frames only where frame numbers ≤ EVERY in-use read-mark; encode snapshot bounds as values protected by their own locks so coordination happens through data.

**Probes:** wal.rs:9768 `test_wal_concurrent_readers_during_checkpoint` pins read-mark clamping; :10286 `test_wal_full_waits_for_old_reader_then_succeeds` pins nbackfills ordering; :9388 `test_read_retry_does_not_leak_vacuum_guard_or_block_vacuum` forces the retry path by occupying ALL FOUR slots and asserts no leaked guard/slot.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "WalSnapshot read mark determine_max_safe_checkpoint_frame BusySnapshot", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt slot-encoded snapshots + data-driven checkpointer clamping verbatim (it IS SQLite's design, hardened); adapt slot count/backoff constants; omit multi-process authority coordination unless needed. MVCC consumers bridge GC floors via min_pinned_read_frame — keep that hook when porting both layers together.
