<!-- capsule-v2 -->
# Connection savepoint frame ledger — how does ROLLBACK TO restore in-memory schemas with ZERO disk I/O while staying on the vdbe async contract?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Where are the in-memory schema snapshots captured and re-installed so a ROLLBACK TO undoes staged DDL without reparsing sqlite_schema from disk (which would block on cursor I/O and violate the vdbe async contract)?

## Frame ledger + snapshot capture
**Path/Symbol:** `core/connection.rs:NamedSavepointFrame` (:124-148), `RollbackFrameInfo` (:150-156); `Connection::with_savepoint_schema_snapshot` (:4847-4864), `push_named_savepoint` (:4838-4840), `rollback_named_savepoint_frame` (:4881-4896).
**Signature:** `pub(crate) fn with_savepoint_schema_snapshot<F, T>(&self, f: F) -> T where F: FnOnce(Arc<Schema>, Option<Arc<Schema>>, HashMap<usize, Arc<Schema>>) -> T`.
**Data Shape:** `NamedSavepointFrame { name: String, starts_transaction: bool, deferred_fk_violations: isize, main_schema_snapshot: Arc<Schema>, temp_schema_snapshot: Option<Arc<Schema>>, staged_schema_snapshot: HashMap<usize, Arc<Schema>> }`; ledger is `named_savepoints: RwLock<Vec<NamedSavepointFrame>>` (:492). Temp snapshot `None` means "temp DB not yet initialized" — a real empty-schema reset at rollback, NOT a skip.

### Decisive source (why snapshots, per the struct's own contract comment)
```rust
// connection.rs :128-137 — the doc comment IS the porting spec
/// Snapshot of `conn.schema` taken at SAVEPOINT begin. Used by
/// ROLLBACK TO to restore the in-memory main schema without re-
/// reading sqlite_schema from disk — disk reparse from inside a
/// vdbe opcode would block on cursor I/O (and additionally, for
/// sequences, on `prepare_internal + run_with_row_callback`),
/// violating the vdbe async contract. Cheap to capture: bumps
/// the `Arc<Schema>` refcount.
```
```rust
// execute.rs :4962-4971 — the three-way restore, order matters
if let Some(info) = frame_info {
    *conn.schema.write() = info.main_schema_snapshot;
    if let Some(temp_db) = conn.temp.database.read().as_ref() {
        match info.temp_schema_snapshot {
            Some(snap) => *temp_db.db.schema.lock() = snap,
            None => *temp_db.db.schema.lock() = conn.empty_temp_schema(),
        }
    }
    *conn.database_schemas().write() = info.staged_schema_snapshot;
    conn.bump_prepare_context_generation();
}
```

**Flow:** SAVEPOINT Begin → op_savepoint calls `with_savepoint_schema_snapshot` which clones all THREE schema Arcs under their existing locks and passes them into the closure that builds the frame → frame pushed AFTER mirror success (:4871). ROLLBACK TO → engine-level page rollback first, then `rollback_named_savepoint_frame` clones the frame's Arcs into `RollbackFrameInfo` and truncates to `target_idx + 1` ("ROLLBACK TO keeps the target savepoint itself on the stack; only nested savepoints above it are discarded", :4892-4894) → opcode installs the snapshots into main/temp/attached schema slots and bumps the prepare-context generation so cached prepared statements re-derive against the restored schema (:4971).
**Invariant:** The snapshot must be captured BEFORE any DDL can run under this savepoint and restored as an Arc swap (no reparse): a porter who "restores by re-reading sqlite_schema" reintroduces blocking I/O mid-opcode AND loses the sequences map (the snapshot carries it whole, :4957-4961). `Arc::make_mut` in `with_schema_mut` means post-savepoint DDL diverges onto a fresh allocation, so the old Arc stays pristine — cheap copy-on-write, no defensive clone needed.
**Probe:** `grep -c 'conn.empty_temp_schema()' core/vdbe/execute.rs` = 2 (restore arm + helper definition context) and `sed -n '4974,4984p' core/vdbe/execute.rs | grep -c 'set_schema_cookie(None)'` = 2 (main pager + attached loop) — pins that cookie invalidation accompanies every schema restore.

## Ledger stack discipline (release vs rollback-to asymmetry)
**Path/Symbol:** `Connection::release_named_savepoint_frame` (:4866-4879) vs `rollback_named_savepoint_frame` (:4881-4896); `with_named_savepoints` read accessor (:4830-4836); `clear_named_savepoints` (:4898-4900).
**Signature:** `pub(crate) fn release_named_savepoint_frame(&self, name: &str) -> SavepointResult`.
**Data Shape:** newest-match resolution via `rposition(|sp| sp.name == name)` (names already ASCII-lowercased at translate time — see `savepoint-name-normalization` capsule).

### Decisive source
```rust
// connection.rs :4874-4878 — Release of a transaction-starting bottom frame = Commit
if savepoints[target_idx].starts_transaction && target_idx == 0 {
    return SavepointResult::Commit;
}
savepoints.truncate(target_idx);          // release DISCARDS the target
// vs :4893-4894 rollback-to KEEPS the target
savepoints.truncate(target_idx + 1);
```

**Flow:** RELEASE resolves newest matching name → if it is index 0 AND started the transaction, return `Commit` (opcode then tail-calls `op_auto_commit`, execute.rs :4810, call site :5183) else truncate target-and-above. ROLLBACK TO returns the frame info and keeps the target for repeated rollback (`savepoint-rollback-to-can-be-repeated`). Full COMMIT/ROLLBACK clears the whole ledger via `clear_named_savepoints()` (connection.rs :4996; called from execute.rs :4858/:5011).
**Invariant:** The two ops differ by EXACTLY ONE on the truncate bound (+1 keeps target). Porters who unify them break repeatable ROLLBACK TO. The `starts_transaction && target_idx == 0` conjunction is load-bearing: a transaction-starting savepoint BELOW another one releases as plain Release (outer frames still hold), only the bottommost commits.
**Probe:** `grep -c 'rposition(|savepoint| savepoint.name == name' core/connection.rs` = 2 (both entry points share newest-match semantics) and `grep -c 'savepoints.truncate(target_idx + 1);' core/connection.rs` = 1 (only rollback-to keeps its target).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "NamedSavepointFrame rollback_named_savepoint_frame with_savepoint_schema_snapshot", limit: 6 });
// turso.core.connection.NamedSavepointFrame Struct core/connection.rs 124-148
// turso.core.connection.Connection.with_savepoint_schema_snapshot Method core/connection.rs 4847-4864
// turso.core.connection.Connection.rollback_named_savepoint_frame Method core/connection.rs 4881-4896
```
Verified live at pin def9a060: all three symbols resolve line-exact; check_index_coverage on core/connection.rs = no_recorded_issue + metadata_match.

## Verdict
Adopt the three-snapshot Arc-capture ledger (main/temp/staged) with generation-bumped restore as the pattern for undoing in-memory DDL state alongside page-level rollback — any engine with async opcode contracts needs snapshot-not-reparse. Adapt the lock shapes (RwLock<Vec>, std sync primitives) to host conventions. Omit the specific `empty_temp_schema` sentinel if the host tracks temp-init differently, but preserve the None-means-reset semantics. Direct tests: sqlite/conformance/sqlite-sqltests/savepoint.sqltest `savepoint-rollback-to-removes-temp-ddl{,-with-dml}` + `savepoint-rollback-to-temp-table-unreachable` (in-memory temp schema must match rolled-back disk); differential fuzz tests/fuzz/savepoint.rs verifies `temp_schema` verify-query parity against rusqlite across 2000-step runs.
