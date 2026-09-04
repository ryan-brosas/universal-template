<!-- capsule-v2 -->
# Logical log recovery — what is the replay boundary, and why must WAL truncation come last in a checkpoint?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How does restart decide which journal frames to replay, and how do the two logs hand durability to each other?

## persistent_tx_ts_max boundary + WAL-last ordering
**Path/Symbol:** `core/mvcc/persistent_storage/logical_log.rs:1-231` (module doc), `core/mvcc/database/mod.rs:4552-4556` (`MVCC_META_KEY_PERSISTENT_TX_TS_MAX`, verified :3650), checkpoint ladder in checkpoint_state_machine.rs (:150-165 doc; TruncateLogicalLog :2801 / FsyncLogicalLog :2827 / SyncDbFile :2876 / TruncateWal :2913).
**Signature:** recovery: validate header (empty/0-byte file = no log) → accept valid-header-with-no-frames (size ≤ LOG_HDR_SIZE) → read `persistent_tx_ts_max` from `__turso_internal_mvcc_meta` → stream frames in commit order until first torn tail → apply only frames with `commit_ts > persistent_tx_ts_max` → set clock to `max(persistent_tx_ts_max, max_replayed_commit_ts) + 1` → restore writer offset to `last_valid_offset` so torn-tail bytes are overwritten.
**Data Shape:** the replay boundary is persisted INSIDE the pager's data (a metadata row), committed atomically with the checkpointed rows in one WAL transaction.

### Decisive source
```text
// logical_log.rs:150-160 — the two-log durability handshake:
// "Checkpoint ordering (enforced by checkpoint state machine):
//  1. write committed MVCC versions into pager (WAL);
//  2. commit pager transaction (data + metadata row in same WAL txn);
//  3. checkpoint WAL pages into DB file;
//  4. fsync DB file (unless SyncMode::Off);
//  5. truncate logical log to 0 (regenerates salt…);
//  6. fsync logical log …;
//  7. truncate WAL last.
//  WAL-last is intentional: if crash happens mid-checkpoint, WAL remains a
//  safety net until logical-log cleanup is complete."
```

The atomicity trick that makes the boundary safe: data and the metadata row ride the SAME pager WAL txn (:3553 test name: `test_meta_checkpoint_case_10_metadata_upsert_is_atomic_with_pager_commit`) — so no crash can leave the boundary claiming frames the DB file doesn't hold.

**Flow:** checkpoint materializes versions into the DB file → advances durable boundary atomically → shrinks logical log → shrinks WAL LAST.
**Invariant:** never truncate either log before its successor is durably in place; recovery clock must exceed every replayed commit_ts.
**Probe:** `test_checkpoint_truncates_wal_last` (tests.rs:2600); `test_bootstrap_completes_interrupted_checkpoint_with_committed_wal` (:2552); `test_empty_log_recovery_loads_checkpoint_watermark` (:3093); TRUNCATE-mode asserts at checkpoint_state_machine.rs:2809-2820 (offset==0 AND file size==0).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "persistent_tx_ts_max truncate wal last recovery", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the boundary-in-the-data + WAL-last ladder verbatim for any dual-journal engine; adapt metadata table naming; omit the salt-regeneration detail only if you keep per-generation CRCs equivalent. Coverage caveat: probes are direct tests in tests.rs; integration restart matrix lives in multiprocess_tests.rs (not run this pass).
