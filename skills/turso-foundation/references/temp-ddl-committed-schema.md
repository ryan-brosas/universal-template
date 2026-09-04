<!-- capsule-v2 -->
# Temp-DDL committed-schema snapshot — how do temp tables roll back when the outer transaction does?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** How is the per-connection in-memory TEMP schema made transactional without any shared schema to publish to?

## TempDbState committed_schema snapshot/restore
**Path/Symbol:** `core/connection.rs` — `committed_schema: RwLock<Option<Arc<Schema>>>` (:105) + `schema_did_change: AtomicBool`, `mark_temp_schema_did_change` (:740-749), `commit_temp_schema` (:754-778), `rollback_temp_schema` (:783-804), `reset_temp_database` (:729-735, called from `set_temp_store` :3891-3897), `empty_temp_schema` (:583); marker opcode arm `Cookie::SchemaVersion where db == TEMP_DB_ID` in `core/vdbe/execute.rs:14778-14782`.
**Signature:** `pub(crate) fn commit_temp_schema(&self)` / `pub(crate) fn rollback_temp_schema(&self)`; restore arms: `Some(snap) => *temp_db.db.schema.lock() = snap, None => *temp_db.db.schema.lock() = self.empty_temp_schema()`.
**Data Shape:** the snapshot is a CLONED `Arc<Schema>` of the temp database's schema taken at commit; the dirty flag is a plain AtomicBool with Release/Acquire ordering.

### Decisive source
```rust
// core/vdbe/mod.rs:2172 — publication timing contract
// Finalize the in-memory TEMP schema only when the outer
// transaction actually finishes. Updating the committed temp
// snapshot after every statement inside an explicit
// transaction would make a later full ROLLBACK restore
// uncommitted temp DDL.
let transaction_finished = self.connection.auto_commit.load(Ordering::SeqCst)
    && self.connection.get_tx_state() == TransactionState::None;
if rollback { conn.rollback_temp_schema(); } else { conn.commit_temp_schema(); }
// execute.rs:14779 — why TEMP needs its own channel:
// TEMP has no shared `Database::schema` to publish to, so
// commit/rollback consult a separate `committed_temp_schema`
```

**Flow:** CREATE/ALTER/DROP on temp → `SetCookie` with `db == TEMP_DB_ID` writes the cookie AND calls `mark_temp_schema_did_change()` → at outer-tx end: commit snapshots current temp schema into `committed_schema` and clears the flag; rollback restores the last snapshot (or empty schema if none ever committed) and bumps `prepare_context_generation` so prepared statements reprepare. `PRAGMA temp_store` change outside a txn tears the whole temp db down via `reset_temp_database`.
**Invariant:** the flag gates BOTH paths symmetrically — no temp DDL this transaction ⇒ both are no-ops (snapshot never goes stale). Snapshot-on-commit means a ROLLBACK restores exactly the last COMMITTED temp shape even across multiple nested DDL statements. The unreachable-state asserts (`schema_did_change set but temp uninitialized`) encode that marking can only happen after `ensure_temp_database`. Rollback also invalidates prepared statements via generation bump — omitting that serves stale plans against the restored schema.
**Probe:** `core/mvcc/database/tests.rs::dropped_main_commit_rolls_back_temp_schema_changes` (:18118 — abandoned mid-yield COMMIT must make `SELECT * FROM temp_only` fail with "no such table" while main-db writes also roll back and integrity_check stays ok); text anchors: `grep -c 'fn commit_temp_schema' core/connection.rs` → 1; `grep -c 'fn rollback_temp_schema' core/connection.rs` → 1; `grep -c 'Finalize the in-memory TEMP schema only when the outer' core/vdbe/mod.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "rollback_temp_schema committed temp schema snapshot", limit: 10 });
```

## Verdict
Adopt the dirty-flag + clone-at-commit + restore-or-empty pattern for any in-memory catalog that must ride an external transaction; adapt storage of the snapshot (here `RwLock<Option<Arc<Schema>>>` on the connection). Omit main/attached DB schema-cookie publishing (`schema.rs` resolution by db id) — covered by other planes.
