<!-- capsule-v2 -->
# Pager durability ordering — where exactly does the one fsync sit between bytes-written and metadata-published?

**Source:** turso (Turso) MIT `main@def9a0601b8ead82675e672e1843447251b15fb4`; Codebase Memory `turso`. **Question:** How does an async-IO commit guarantee recovery never replays bytes that were not durable?

## Eight-state commit pipeline; fsync only after ALL write completions
**Path/Symbol:** `core/storage/pager.rs` commit pipeline ending …WaitWrites → WaitSync → WalCommitDone → AutoCheckpoint; partial-write rationale :4351-4358; ≤1-inflight-fsync assert (:4366 "WaitSync expects at most one in-flight fsync completion"); sync-failure refusal (:3131 via get_data_sync_retry); evicted-dirty read-error surfacing (:4185-4196 "page-buffer-not-loaded panic in prepare_frames"); auto-checkpoint decoupling doc (:1027).
**Data Shape:** CommitInfo carries per-write completions; WaitSync re-entry waits on a pending fsync completion instead of submitting a second.

### Decisive source
```rust
// To protect against partial writes, we MUST ensure that all write Completions
// finish before submitting the fsync. It is possible that a partial write will
// cause an IO backend to resubmit the write (particularly with io_uring) and we
// cannot have the fsync submitted before all writes are fully done, even if
// they are IO_LINK'd together or we submit the fsync with IO_DRAIN, the only way
// to ensure durability in the case of partial writes is to ensure the pwritev
// completes before the fsync is submitted.
```
(pager.rs:4351-4358)

**Flow:** writes complete → synchronous read errors on evicted dirty pages surface IMMEDIATELY ("otherwise we would silently drop the failure… and later trip the page-buffer-not-loaded panic", :4185-4196) → exactly ONE fsync between bytes and metadata (asserted ≤1 in flight) → on fsync error with data_sync_retry=off, PANIC mirroring SQLite's refusal to continue after ambiguous sync failures → WAL metadata published strictly AFTER fsync success.
**Invariant:** Durability is an ORDERING property, not an IO property: enumerate every way an async backend can reorder or resubmit, place exactly one fsync between "bytes written" and "metadata published," assert it in code. Auto-checkpoint runs OUTSIDE the transaction — "checkpoint failure does not affect commit durability" (:1027).

**Probe:** `core/storage/pager.rs:6781 checkpoint_db_sync_completion_still_leaves_backfill_unpublished_until_proof_install` pauses the state machine in the post-sync gap and asserts nbackfills stays 0 until durable proof installs — DB-file sync alone never publishes progress.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "WaitSync commit_wal_inner data_sync_retry AutoCheckpoint", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the completion-barrier-before-fsync rule verbatim for any io_uring-style backend; adopt the panic-on-ambiguous-sync stance and the assert-≤1-fsync guard; keep auto-checkpoint outside commit semantics. Adapt state-machine shape to your IO runtime; omit nothing from the barrier itself.
