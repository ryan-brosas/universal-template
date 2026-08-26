<!-- capsule-v2 -->
# Checkpoint durability ladder — in what order must the MVCC checkpoint touch WAL, DB file, logical log, and WAL truncation?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** After committing the pager txn, what is the exact fsync/truncate ladder that makes the checkpoint crash-safe?

## SyncDbFile → publish backfill → TruncateLogicalLog → FsyncLogicalLog → TruncateWal
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs:SyncDbFile` (:2876-2911), `CheckpointWal` (:2840-2875), `TruncateWal` (:2913+), `TruncateLogicalLog` (:2801-2825), `FsyncLogicalLog` (:2827), state doc (:92-99).
**Signature:** SyncDbFile skips when `synchronous=off` or `wal_checkpoint_backfilled == 0`, guards re-entry with `db_sync_sent`, and calls `publish_wal_backfill_if_needed()` only after sync; TruncateWal runs ONLY for modes where `should_restart_log()` and re-acquires the blocking lock because "Truncate/Restart renumbers WAL frames — only safe stop-the-world."
**Data Shape:** passive Busy under a pinned DbFile reader degrades to "continue without backfill" (`Err(LimboError::Busy)` arm at :2866-2874) — checkpoint still succeeds, versions stay retained for low-frame readers.

### Decisive source
```text
// checkpoint_state_machine.rs:92-95 — why the fsync sits before truncations:
// "SyncDbFile … Fsync the database file after checkpoint, before truncating
//  WAL. This ensures durability: if we crash after WAL truncation but before
//  DB fsync, the data would be lost."
// :2915-2918:
//   "Truncate/Restart renumbers WAL frames — only safe stop-the-world."
// :2933-2939 — final publication + GC floor:
//   durable_txid_max.store(durable_txid_max_new); backfill_floor = current
//   wal position — "a version materialized at or below it is durable in the
//   DB file, hence reachable by every snapshot."
```

Finalize asserts no staged-but-unpublished schema roots survive ("checkpoint finalized with un-published staged schema roots") and computes the LWM-driven GC pass afterwards.

**Flow:** backfill WAL→DB → fsync DB → publish backfill boundary (GC floor) → truncate logical log (+ assert zeroed on TRUNCATE mode) → fsync logical log → truncate/restart WAL last.
**Invariant:** each log may shrink only after its successor holds the data durably; never publish a positive backfill count before the DB file is synced.
**Probe:** `test_full_checkpoint_reopen_recovers_truncate_mode` (tests.rs:2850); `test_recovery_checkpoint_then_more_writes` (:2241); in-machine asserts at :2809-2820 pin offset==0 and file size==0 after TRUNCATE-mode logical-log reset.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "SyncDbFile TruncateWal publish_wal_backfill backfill_floor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder verbatim for any engine with two journals plus a page file; adapt skip-guards to your sync modes; omit WAL-restart locking if you never renumber frames. Coverage caveat: none material.
