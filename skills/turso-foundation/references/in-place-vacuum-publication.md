<!-- capsule-v2 -->
# In-place VACUUM state machine — how do you replace every page of a live database through its own WAL without ever exposing a torn image?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What is the commit boundary that makes a whole-database physical rewrite atomic for readers, and which resources must survive each failure?

## Phase machine + independent cleanup ledger
**Path/Symbol:** `core/vdbe/vacuum.rs:VacuumInPlacePhase` (:1261-1336) / `vacuum_in_place_step` (:1699-2320); cleanup ledger `VacuumInPlaceCleanupState` (:1248-1258).
**Signature:** `fn vacuum_in_place_step(connection, db, phase, temp_db, committed_image, cleanup_state) -> Result<IOResult<()>>`.
**Data Shape:** 12 phases Preflight → BeginSourceTx → ReadSourceMetadata → TargetBuild → CaptureTargetMetadata → BeginTempReadTx → InitSourceWalHeader? → ReadTempBatch ⇄ WriteWalBatch → (SyncSourceWal)? → PublishWalCommit → Checkpoint → InstallCommittedImage → Done; ledger tracks `{mvcc_guard, checkpoint_cleanup ∈ {None,ReleaseRaw,AbortCheckpoint}, source_tx_open, vacuum_lock_held}` — deliberately NOT owned by the phase enum.

### Decisive source (the atomicity hinge)
```rust
// :2205-2247 PublishWalCommit
wal.finish_append_frames_commit()?;          // frames become THE committed image
source_pager.end_write_tx();
cleanup_state.source_tx_open = false;
connection.auto_commit.store(true, Ordering::SeqCst);
connection.set_tx_state(TransactionState::None);
// Invalidate page cache and schema cookie so fresh reads see
// the newly committed WAL frames.
source_pager.clear_page_cache(false);
source_pager.set_schema_cookie(None);
// Drop temp resources before checkpoint.
drop(temp_db.take().expect(...));
```
Copy-back batches stream temp pages into the SOURCE WAL via `prepare_frames(batch_pages, page_sz, db_size_on_commit, prev_prepared)` where only the LAST batch passes `db_size_on_commit = Some(total_pages)` (:2070-2077), then write via `IOWriteBatch`, then `commit_prepared_frames` per batch to advance connection-local page→frame/max_frame/checksum state (:2130-2145). The temp DB is WAL-only by construction (`wal_auto_actions_disable()` at open :321; asserted: db file holds exactly page 1, `temp_db_file_size == temp_page_size`, :1912-1925).

**Flow:** Preflight rejects {in-txn, concurrent statements ≠ 1, readonly, in-memory, Incremental auto-vacuum, non-WAL} then takes the MVCC gate (see mvcc-vacuum-gate-ladder) and `try_begin_vacuum_checkpoint_lock` EARLY so the post-commit TRUNCATE cannot lose a race (:1785-1790) → BeginSourceTx `begin_vacuum_blocking_tx()` grabs vacuum lock + WAL write lock + snapshot in one shot → TargetBuild builds the compacted image in a file-backed `etilqs_` temp DB through the shared 13-phase `VacuumTargetBuildPhase` engine (:479-1031: create tables → copy rows → create indexes AFTER data → triggers/views/rootpage=0 last → finalize header w/ schema_cookie+1 :222) → capture metadata snapshot BEFORE publish (header + reparsed schema with sequences grafted to avoid blocking reloads, :1612-1638) → batch copy-back → publish → forced `SyncMode::Full` TRUNCATE checkpoint via `vacuum_checkpoint_with_held_lock` asserting `result.should_truncate()` (:2259-2270) → install captured image.

### Decisive source (failure after publish is NOT a rollback)
```rust
// :2285-2300 Checkpoint error arm
Err(err) => {
    tracing::error!("VACUUM post-commit checkpoint failed: {err}");
    source_pager.cleanup_after_checkpoint_failure();
    cleanup_state.checkpoint_cleanup = CheckpointLockCleanup::None;
    let committed_image = committed_image.take().expect(...);
    install_committed_vacuum_image(connection, db, &committed_image); // infallible install
    ... release vacuum lock ... return Err(err);
}
```
Cleanup (:2330-2403) keys on the LEDGER, not the phase: pre-publish failure ⇒ drop TargetBuild helper statements FIRST ("live helper statements keep Connection::nestedness > 0, making rollback_tx a no-op" :2378-2381) then `pager.rollback_tx`; post-publish failure ⇒ nothing to undo, still installs the committed image. Mirror-failure during SAVEPOINT-style partial mirror opens uses blind idempotent release (same pattern as op_savepoint Begin).

**Invariant:** The single publication point is `finish_append_frames_commit()` — before it, every failure rolls back cleanly; after it, NO code path may treat the source tx as abortable, and even checkpoint failure must surface success-shaped state (committed image installed) with an error. Readers never see a torn image because they read published max_frame, not bytes-in-flight.
**Probe:** `grep -c 'fn ' <(grep -n '#\[test\]' -A1 core/vdbe/vacuum.rs | grep 'fn ')` ≥ 19 tests incl. sync-count pins `in_place_vacuum_with_sync_off_syncs_source_db_once_and_wal_twice` / `in_place_vacuum_with_sync_full_adds_pre_publish_wal_sync`; runnable `cargo test --features conn_raw_api -p turso_core --lib vacuum::`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "MvccVacuumGuard vacuum_in_place_step VacuumInPlacePhase coalesce_frame_runs", limit: 8 });
// turso.core.vdbe.vacuum.vacuum_in_place_step Function core/vdbe/vacuum.rs 1699-2320
// turso.core.vdbe.vacuum.coalesce_frame_runs Function core/vdbe/vacuum.rs 1458-1487
```

## Verdict
Adopt the build-elsewhere→publish-through-WAL→checkpoint shape, the one-batch-lagged pipeline (next batch's reads kick off while previous writes complete), contiguous frame-run coalescing (`coalesce_frame_runs` sorts `(page, frame)` by frame id so one pread serves many logical pages, uniqueness hard-asserted :1464-1476), and the ledger-keyed cleanup with nestedness-drop-before-rollback. Adapt temp-db naming/paths. Omit SQLite vacuum.c parity comments as normative. Coverage: cited paths `no_recorded_issue`.
