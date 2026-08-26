<!-- capsule-v2 -->
# Statement savepoint lifecycle — how is one statement's partial write undone inside an explicit transaction?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** Where do statement subtransactions open/close, and which backends (MVCC store vs pager subjournal vs attached pagers) own the undo?

## ProgramState::begin_statement / end_statement
**Path/Symbol:** `core/vdbe/mod.rs::ProgramState` — `begin_statement` (:1233-1273), `end_statement` (:1281-1395), `EndStatement::{ReleaseSavepoint,RollbackSavepoint}` (:1447-1454); opcode entry `OpTransactionState::BeginStatement` in `core/vdbe/execute.rs:4461-4525`; cleanup dispatch on `TxnCleanup` at `core/vdbe/mod.rs:2893-2930`.
**Signature:** `pub fn begin_statement(&mut self, connection: &Connection, pager: &Arc<Pager>, write: bool) -> Result<IOResult<()>>`; `pub fn end_statement(&mut self, connection: &Connection, pager: &Arc<Pager>, end_statement: EndStatement) -> Result<()>`.
**Data Shape:** state flags `has_stmt_transaction`, `uses_subjournal`, `is_active_write`, `attached_savepoint_pagers: Vec<Arc<Pager>>`, plus FK counters `fk_deferred_violations_when_stmt_started` and `fk_immediate_violations_during_stmt`.

### Decisive source
```rust
// core/vdbe/mod.rs:1277 — the independence contract
// Mirrors SQLite's vdbeCloseStatement (vdbeaux.c:3203-3248). Pager/MVCC
// savepoint management and FK violation counter restoration are independent
// concerns: pager savepoints may be skipped (e.g. autocommit optimization)
// while FK bookkeeping still needs cleanup.
// RollbackSavepoint arm: main pager uses rollback_to_newest_savepoint when
// uses_subjournal, MVCC uses mv_store.rollback_first_savepoint(tx_id),
// each attached pager rolled back in a loop collecting FIRST error only —
// then FK counters restored UNCONDITIONALLY (:1372-1379).
```

**Flow:** statement start → if `needs_stmt_subtransactions && write && in_explicit_txn`: main DB opens an MVCC store savepoint (`mv_store.begin_savepoint`) OR a pager savepoint + subjournal (`open_subjournal → try_use_subjournal → open_savepoint(db_size)`, stopping subjournal use if open fails); attached DBs get per-pager savepoints only when they actually write inside an explicit txn. Statement end → ReleaseSavepoint pops them; RollbackSavepoint rewinds newest-to-first and always restores FK counters.
**Invariant:** begin/end are asymmetric by design — a savepoint may never have been opened (autocommit single-statement path skips it) yet `end_statement` must still run to decrement `n_active_writes` and restore FK counters. Attached-pager rollback collects the first error but still unwinds every remaining pager before returning. `fk_deferred_violations` is snapshotted at statement START so an inner rollback cannot lose violations accrued by earlier statements of the same interactive transaction.
**Probe:** `tests/fuzz/subjournal.rs::subjournal_tests` (differential vs rusqlite over SAVEPOINT/DML histories; generator header :30-38 maps tables t/t_auto/t_bare/t_trig/t_pidx/child onto stmt_journal toggle paths); text anchors: `grep -c 'fn begin_statement' core/vdbe/mod.rs` → 1; `grep -c 'fn end_statement' core/vdbe/mod.rs` → 1; `grep -c 'rollback_to_newest_savepoint' core/vdbe/mod.rs` → 3; `grep -c 'uses_subjournal = true' core/vdbe/mod.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "begin_statement end_statement subjournal savepoint", limit: 10 });
```

## Verdict
Adopt the three-backend savepoint routing (MVCC savepoints / pager subjournal / attached pagers) and unconditional-FK-restore rule; adapt backend names to your storage layer; omit the fuzz corpus itself.
