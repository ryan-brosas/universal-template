<!-- capsule-v2 -->
# MVCC checkpoint state machine — in what order do version-store rows reach the B-tree, and why is WAL truncation last?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** When materializing MVCC versions into the SQLite-compatible file, what ordering makes a mid-checkpoint crash always recoverable?

## Enumerated states with fsync-then-truncate ordering baked into the enum
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs:60-115` (`enum CheckpointState`: PrepareCheckpoint → AcquireLock → BuildLocalSchemaView → CollectTableRows/CollectIndexRows → BeginPagerTxn → WriteRow{StateMachine}/DeleteRowStateMachine/WriteIndexRow* → CompactSequences → CommitPagerTxn → CheckpointWal → SyncDbFile → TruncateLogicalLog → FsyncLogicalLog → TruncateWal → GcTableRows/GcIndexRows{lwm} → Finalize), driver trait `core/state_machine.rs:3-27` (`StateTransition::step` returning `TransitionResult::{Io,Continue,Done}`).
**Signature:** `fn step(&mut self, context: &Context) -> Result<TransitionResult<SMResult>>`; machine loops until Done or yields as `IOResult::IO`.
**Data Shape:** write/delete/index states carry a `write_set_index` cursor so any state can resume after an IO yield; GC states carry the `lwm` used to reclaim version-store rows AFTER their content is durably in the B-tree.

### Decisive source
```rust
// checkpoint_state_machine.rs:96-101 — the enum documents its own ordering:
    /// Fsync the database file after checkpoint, before truncating WAL.
    /// This ensures durability: if we crash after WAL truncation but before DB fsync,
    /// the data would be lost.
    SyncDbFile,
    TruncateLogicalLog,
// logical_log.rs:146-153 — the same contract from the log side:
//! 5. truncate logical log to 0 ...
//! 7. truncate WAL last.
//! WAL-last is intentional: if crash happens mid-checkpoint, WAL remains a safety net
```
Collection is chunked (`COLLECT_PREEMPTION_THRESHOLD = 1024`) and root-page mutations are STAGED during collection then published in one window (`RootMapOp::{Alloc,SetEnd...}` :137+), so readers never see half-published root bindings. Sequence compaction notes WHY it lives here: inline compaction was removed from the hot path "to eliminate shared-row WW conflicts" — checkpoint is the single-writer moment that can safely reclaim.

**Flow:** snapshot write set → per-row btree write via sub-state-machines (each yields on IO) → commit pager txn (data + metadata in ONE WAL txn) → backfill → fsync DB → truncate logical log → fsync log → truncate WAL LAST → GC version store below lwm.
**Invariant:** no truncation before its successor's durability proof; GC only after Finalize-safe materialization; every yield point must be resumable from the carried cursor alone.
**Probe:** yield-injection harness `CheckpointYieldPoint` (:118+: BeforeAcquireLock / AfterDurableBoundaryAdvanced / AfterCollectTableRows / BeforePagerCommit) drives resumption tests; pager-side twin `checkpoint_db_sync_completion_still_leaves_backfill_unpublished_until_proof_install` (pager.rs) pins the publish-after-proof rule.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "CheckpointState SyncDbFile TruncateWal GcTableRows", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the enumerated-resumable-states pattern for any multi-gigabyte materialization; adapt the specific orderings to your log topology but keep "truncate the oldest recovery source LAST". Omit sequence compaction unless you port sequences.
