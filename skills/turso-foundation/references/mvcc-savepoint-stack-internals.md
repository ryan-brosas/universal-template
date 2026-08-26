<!-- capsule-v2 -->
# MVCC savepoint stack — how do you roll back individual statements and named savepoints inside an uncommitted optimistic transaction without copying data?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What exactly must be recorded per savepoint so a rollback restores version chains, the write set, header, AND deferred-FK state — no more, no less?

## Savepoint record + ledger fields
**Path/Symbol:** `core/mvcc/database/mod.rs:Savepoint` (:838-916), `SavepointKind` (:825-834), `Transaction::rollback_savepoint_changes` (:6711-6814).
**Signature:** `fn named(name: String, starts_transaction: bool, deferred_fk_violations: isize, header: DatabaseHeader, header_dirty: bool)`; `fn merge_from(&mut self, other: Savepoint<A>)`.
**Data Shape:** per-savepoint delta ledgers: `created_{table,index}_versions: Vec<(key, version_id)>`, `deleted_{table,index}_versions: Vec<(key, version_id)>` (end-timestamp was SET), `newly_added_to_write_set: Vec<(RowID, RowVersions<A>)>`; plus snapshots `{header, header_dirty, deferred_fk_violations}`. Stack lives on `Transaction.savepoint_stack: RwLock<Vec<Savepoint>>` (:1005).

### Decisive source (undo semantics per ledger class)
```rust
// mod.rs :6734-6748 created ⇒ REMOVE the chain entry
for (rowid, version_id) in created_table_versions {
    if let Some(entry) = self.rows.get(&rowid) {
        let mut versions = entry.value().write();
        let before = versions.len();
        versions.retain(|rv| rv.id != version_id);   // delete the uncommitted insert
        self.dec_live_version_count_approx(before - versions.len());
    }
}
// :6766-6782 deleted ⇒ CLEAR end (restore visibility)
for (rowid, version_id) in deleted_table_versions {
    for rv in versions.iter_mut() { if rv.id == version_id { rv.set_end(None); break; } }
}
// :6804-6813 write_set + header restore
touched_rowids.extend(newly_added_to_write_set.into_iter().map(|(id, _)| id));
self.remove_rolled_back_rows_from_write_set(tx_id, touched_rowids.clone());
*tx.header.write() = header;                        // snapshot restore
tx.header_dirty.store(header_dirty, Ordering::Release);
```

**Flow:** every mutation records into the TOP of stack (`insert_to_write_set` :1059-1077 — "Duplicates here are harmless ... gated by `row_has_uncommitted_version_for_tx`"); statement scope = auto-pushed `SavepointKind::Statement` (`begin_savepoint` :1080-1088); named scope = pushed on SAVEPOINT opcode with `starts_transaction = conn.auto_commit` captured at that instant (execute.rs :4788). Release pops and **merges** child deltas into parent (`merge_from` :905-916 — "so outer rollback still has a full undo set"). Rollback-to walks drained savepoints NEWEST-LAST (`for sp in rolledback.into_iter().rev()` at MvStore level :6704-6706) then RE-PUSHES the target as a fresh frame with its original name/fk-snapshot/header (:1218-1225 pager.rs twin :2162-2168).

### Decisive source (write-set eviction is conditional)
```rust
// mod.rs :6844-6862
// Single pass: drop entries that appear in `rowids` AND have no
// surviving uncommitted version (parent savepoints may still pin
// them).
write_set.retain(|rowid, _rv| {
    if !rowids.contains(rowid) { return true; }
    self.row_has_uncommitted_version_for_tx(rowid, tx_id)
});
```

**Invariants:** (1) Rollback removes only versions CREATED in the rolled-back scopes and un-deletes only versions DELETED there — never touches sibling chains. (2) A rowid leaves the write set ONLY if no uncommitted version for THIS tx survives anywhere above (parent may pin it). (3) Named-release of the root frame when `starts_transaction && target_idx == 0` returns `Commit` but DEFERS all mutation until commit succeeds ("If commit fails (e.g. deferred FK violation), savepoints must remain intact" :1173-1177). (4) Header + dirty bit are transaction-local snapshots restored byte-for-byte.
**Probe:** `grep -n 'fn test_savepoint_multiple_statements_last_fails\|fn test_savepoint_same_row_multiple_statements\|fn test_savepoint_index_multiple_statements\|fn test_savepoint_insert_delete_then_fail' core/mvcc/database/tests.rs` → 4 hits (:11821, :11859, :11899, :11961); runnable `cargo test --features conn_raw_api -p turso_core --lib test_savepoint_`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "begin_named_savepoint release_named_savepoint rollback_to_named_savepoint Savepoint merge_from", limit: 8 });
// turso.core.mvcc.database.mod.Transaction.begin_named_savepoint Method core/mvcc/database/mod.rs 1093-1115
// turso.core.mvcc.database.mod.Transaction.rollback_to_named_savepoint Method core/mvcc/database/mod.rs 1191-1230
```

## Verdict
Adopt delta-ledger savepoints (created/deleted/newly-written + header/fk snapshots) over page-image savepoints in any MVCC port; adopt conditional write-set eviction and deferred root-commit. Adapt the lock types. Omit tracing. Coverage: cited paths `no_recorded_issue`.
