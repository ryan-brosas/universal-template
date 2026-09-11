<!-- capsule-v2 -->
# Shared-WAL commit publication — how does multi-process state advance monotonically when any writer can be behind another?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** When process A commits while process B has already advanced the shared header, what prevents A's stale write from hiding B's frames?

## fetch_max everywhere + checksums only-if-latest + visibility_generation counter
**Path/Symbol:** `core/storage/shared_wal_coordination.rs:1350-1375` (`publish_commit`), :1381-1388 (`publish_backfill`), :1235-1273 (`install_snapshot`, trims frame index BEFORE publishing), :1187-1215 (`snapshot()` seqlock read).
**Signature:** `pub(crate) fn publish_commit(&self, max_frame: u64, checksum_1: u32, checksum_2: u32, transaction_count: u64)` — precondition: caller holds the WAL writer lock.
**Data Shape:** shared mmap header of atomics (max_frame, nbackfills, transaction_count, visibility_generation, checkpoint_seq/epoch, page_size, salts, checksums); `SharedWalCoordinationHeader::BYTE_LEN = 76`, magic `TSHMWAL\0`, version-gated decode.

### Decisive source
```rust
// :1359-1369 — the whole lesson in one block:
// Use fetch_max to ensure we never lower max_frame. In multi-process
// mode, another process may have committed frames after ours, advancing
// max_frame beyond our local value. Overwriting with a smaller value
// would make those later frames invisible to checkpoints, causing data loss.
header.max_frame.fetch_max(max_frame, Ordering::AcqRel);
// Only update checksums if we are the latest writer (our max_frame is the current max).
if header.max_frame.load(Ordering::Acquire) == max_frame {
    header.checksum_1.store(checksum_1, Ordering::Release);
```
Counters that mean "at least" use fetch_max (`transaction_count` too); the scalar that means "how many times did visibility change" uses fetch_add. Readers take a consistent view via a seqlock: `snapshot_seq` odd = writer in-flight ⇒ spin; read all fields; re-read sequence; retry on change (:1190-1213). `install_snapshot` orders index-trim before header-publish so later appends can't observe a stale tail.

**Flow:** local WAL write+fsync → writer lock → publish_commit {fetch_max frame; conditional checksum store; bump generation} → release.
**Invariant:** monotonic fields may NEVER be plain stores; derived values (checksums) attach to identity (only the max-writer writes them); readers must validate sequence stability, not trust field reads individually.
**Probe:** in-file tests: `shared_wal_coordination_publish_commit_keeps_monotonic_transaction_count`, `mapped_shared_wal_coordination_snapshot_waits_for_stable_sequence`, `shared_wal_coordination_header_round_trips`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "publish_commit fetch_max visibility_generation snapshot_seq", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fetch_max semantics for any cross-process high-water mark; adapt the seqlock to your atomics budget. Omit salts/checksums if your shared header carries no format-identity state.
