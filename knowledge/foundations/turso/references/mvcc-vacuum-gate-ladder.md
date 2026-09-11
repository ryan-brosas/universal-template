<!-- capsule-v2 -->
# MVCC vacuum stop-the-world gate — how can a physical rewrite run under MVCC without racing logical readers?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How do you prove zero concurrent MVCC transactions before wiping the version store, and what must be re-seeded afterward?

## Gate ladder (RAII)
**Path/Symbol:** `core/vdbe/vacuum.rs:MvccVacuumGuard` (:1195-1228) + `core/mvcc/database/mod.rs:MvStore::try_begin_vacuum_gate` (:4448-4468).
**Signature:** `fn acquire(connection: Arc<Connection>, mv_store: Arc<MvStore>) -> Result<Self>`; `fn demote_connection(&mut self)`; `impl Drop`.
**Data Shape:** guard owns `{connection, mv_store, connection_demoted: bool}`; acquired in Preflight only when `source_db.mvcc_enabled()` (vacuum.rs :1746-1753).

### Decisive source
```rust
// mod.rs :4448-4463
/// This is the same lock used by MVCC checkpointing. All MVCC transactions
/// hold it in read mode for their whole lifetime, so acquiring it in write
/// mode proves there are no active MVCC transactions and prevents new ones
/// from starting until VACUUM releases it.
pub(crate) fn try_begin_vacuum_gate(&self) -> Result<()> {
    if !self.blocking_checkpoint_lock.write() {
        return Err(LimboError::Busy);
    }
    turso_assert!(
        self.txs.is_empty(),
        "MVCC vacuum gate acquired while transactions are still active"
    );
    Ok(())
}
// vacuum.rs :1221-1227 — Drop promotes BEFORE releasing the gate
if self.connection_demoted && self.connection.is_mvcc_bootstrap_connection() {
    self.connection.promote_to_regular_connection();
}
self.mv_store.release_vacuum_gate();
```

**Flow:** Preflight acquires gate (`try_begin_vacuum_gate`, Busy on contention) → fail-closed check `has_uncheckpointed_log()` (logical-log file size ≠ 0 ⇒ error "run PRAGMA wal_checkpoint(TRUNCATE) first", :1754-1758 / mod.rs :4470-4474) → assert this connection holds NO MVCC tx post-gate (hard assert :1759-1768) → `demote_connection()` flips `is_mvcc_bootstrap_connection` so the connection reads schema-cookie state from the pager-backed DB image instead of the MV store (:1769-1772, connection.rs :1113-1128) → conservative `reload_physical_schema_for_mvcc_vacuum` reparse (:1669-1692; uses `reparse_schema_with_cookie_keeping_sequences` because plain `populate_sequences` blocks on IO and violates the vdbe async contract inside the state machine) → guard parked in `cleanup_state.mvcc_guard` → dropped at `InstallCommittedImage` (:2309) and in BOTH cleanup exits (:2373, :2401).

### Decisive source (post-VACUUM wipe)
```rust
// mod.rs :4483-4516 — caller must hold the gate
pub(crate) fn reset_after_vacuum(&self, header: DatabaseHeader, schema: &Schema) {
    turso_assert!(self.txs.is_empty(), ...);
    self.drop_unused_row_versions();
    turso_assert!(!has_table_versions, "requires checkpointed table versions to be cleared");
    turso_assert!(... finalized_tx_states.is_empty(), ...);
    // Drop empty buckets left by checkpoint GC: their table_ids reference
    // pre-VACUUM root pages and can alias new objects after root-page reuse
    self.rows.clear();
    self.index_rows.clear();
    // ... then rebuild table_id_to_rootpage / last_rowid from `schema`
}
```

**Invariant:** The gate converts "physical rewrite vs concurrent logical readers" into a *proven quiesce* — write-mode on the same lock every tx holds read-mode for life. The wipe asserts are the proof nothing logical (rows, index chains, finalized-tx cache, stale empty buckets) survives into the new physical image; skipping the empty-bucket clear corrupts `index_rows` lookups after root-page reuse.
**Probe:** `grep -n 'fn mvcc_active_read_tx_blocks_vacuum_gate\|fn mvcc_active_write_tx_blocks_vacuum_gate\|fn mvcc_vacuum_gate_blocks_new_read_and_write_tx\|fn mvcc_reset_after_vacuum_installs_header_and_rootpages\|fn mvcc_reset_after_vacuum_clears_checkpointed_empty_version_buckets' core/mvcc/database/tests.rs` → 5 hits (:407, :423, :443, :493, :1242); runnable `cargo test --features conn_raw_api -p turso_core --lib vacuum_gate`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "MvccVacuumGuard vacuum_in_place_step try_begin_vacuum_gate reset_after_vacuum", limit: 8 });
// turso.core.vdbe.vacuum.vacuum_in_place_step Function core/vdbe/vacuum.rs 1699-2320
// turso.core.mvcc.database.mod.MvStore.try_begin_vacuum_gate Method core/mvcc/database/mod.rs 4454-4463
// turso.core.mvcc.database.mod.MvStore.reset_after_vacuum Method core/mvcc/database/mod.rs 4483-4549
```

## Verdict
Adopt the gate-as-shared-lock quiesce protocol, the uncheckpointed-log fail-closed precondition, demote/reload/promote ordering (promote strictly before gate release), and the assert-heavy wipe with bucket clearing. Adapt lock primitives to host concurrency toolkit. Omit the specific pragma strings. Coverage: cited paths `no_recorded_issue`, generation_matches=true.
