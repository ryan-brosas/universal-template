<!-- capsule-v2 -->
# DurableStorage port boundary — how do you swap the MVCC commit's durability backend without touching the commit state machine?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Which operations must a pluggable storage implement, which are defaulted, and what handshake keeps lock-free checkpoint checks honest when the real offset lives behind a lock?

## 20-method trait + shadow-offset pattern + default-method extension points
**Path/Symbol:** `core/mvcc/persistent_storage/mod.rs:25-131` (`pub trait DurableStorage`, whole trait), concrete impl :133-293 (`Storage`), lock-free gate `should_checkpoint` :255-261 + shadow maintenance `shadow_offset_store`/`shadow_offset_advance` :156-163. Commit-machine choreography: `core/mvcc/database/mod.rs` — upgrade :3114-3121, `log_tx` :3143, `on_log_write_complete` :3154, sync-skip :3160-3168, offset advance in CommitEnd :3250-3254, abort path `discard_pending_log_write` :1732.
**Signature:** `fn log_tx(&self, m: LogRecord, on_serialization_complete: OnSerializationComplete<'_>) -> Result<(Completion, u64)>` — returns bytes written; caller MUST later call exactly once `advance_logical_log_offset_after_success(bytes)` (CommitEnd) or `discard_pending_log_write()` (abort). Default methods: `on_log_write_complete` (yield completion), `on_checkpoint_start`/`on_checkpoint_end`, `encryption_ctx` (None).
**Data Shape:** `truncate(checkpointed_through_ts) -> (Completion, LogicalLogTruncateOutcome::{Truncated,Retained})` — outcome distinguishes "cut to boundary" from "kept uncheckpointed tail"; `reset_to_fresh_header` exists for external restore (future replay must start from the restored image, not stale local frames).

### Decisive source
```rust
// mod.rs:134-138 + 254 — WHY the shadow exists:
pub struct Storage {
    pub logical_log: RwLock<LogicalLog>,
    /// Shadowed from LogicalLog::offset for lock-free should_checkpoint() reads.
    log_offset: AtomicU64,
// should_checkpoint(): threshold < 0 ⇒ disabled; else shadow >= threshold.
// Every mutation of the canonical offset under the write lock mirrors into the
// atomic (truncate → store new, reset_to_fresh_header → store 0,
// advance_logical_log_offset_after_success → fetch_add(bytes)).
```
The two-phase contract spans the trait boundary: `log_tx` writes at the CURRENT offset without advancing it (`log_tx_deferred_offset`), so a crash between write and confirm leaves the bytes orphaned-but-overwritable; only CommitEnd's `advance_logical_log_offset_after_success(append_bytes)` makes them owned. The commit machine holds the pager commit lock across this window precisely because the next committer would otherwise append over unconfirmed bytes (:3228-3232 rationale).

**Flow:** BuildLogRecord → UpgradeLogicalLogHeader (optional header-version write, caller waits) → WriteLogicalLog = log_tx (frame+write, offset NOT advanced) → FinishLogicalLogWrite = on_log_write_complete (extra durability hook) → SyncLogicalLog (skipped unless synchronous=FULL) → EndCommitLogicalLog (header publish via fetch_max monotonicity) → CommitEnd = advance offset THEN mark Committed THEN rewrite versions. Abort anywhere before CommitEnd ⇒ discard_pending_log_write clears the staged CRC (#7991).
**Invariant:** implementations must keep the shadowed atomic equal to the durable end-of-log after every operation ("once no write is in flight, shadow == on-disk durable offset", aristo intent :220) or checkpointing silently stops/never fires; every trait method that moves the canonical offset MUST mirror the shadow update inside itself — callers never see both sides.
**Probe:** `tests/integration/mvcc.rs:185-226` `test_mvcc_custom_durable_storage_injected` — wraps default storage with a recording impl, asserts an INSERT routes through injected `log_tx`; regression `core/mvcc/persistent_storage/discard_pending_tests.rs:18` pins abort-path CRC discard (success path must PANIC if pending slot missing rather than chain a ghost CRC).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "DurableStorage log_tx should_checkpoint discard_pending_log_write advance_logical_log_offset_after_success", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the trait shape for any swappable durability backend: explicit upgrade/log/sync/truncate/reset verbs, defaults for optional hooks, and a byte-count handshake instead of internal offsets so implementers can't desync the writer position. Adopt the shadow-atomic whenever a hot check must read state owned by a cold lock. Adapt method granularity to your fsync model. Omit encryption_ctx plumbing until at-rest crypto is actually a requirement.
