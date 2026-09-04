<!-- capsule-v2 -->
# Autocommit cleanup arming — why does COMMIT arm RollbackTxn, and how do parked commits and sibling readers decide who may end the transaction?

**Source:** turso (Limbo) MIT `main@f1800bb8c`; Codebase Memory project `turso`. **Question:** After a COMMIT opcode flips `auto_commit` back on but its WAL write then fails, what state makes the failed transaction roll back instead of lingering — and which statement is allowed to finish that rollback?

> **Reconciliation note (pass 15):** `failed-commit-wal-rollback-latch.md` (sibling-authored same wave) pins the arming fix + simulator regression. THIS capsule is the complementary half — the `can_autocommit_now` gating plane that decides WHO may act on the armed latch. Reconcile by folding this Path/Symbol + Invariant block INTO the latch capsule, then delete this file.

## TxnCleanup::RollbackTxn as the "I own ending this tx" baton
**Path/Symbol:** enum `TxnCleanup {None, RollbackTxn, RollbackSavepoint}` `core/vdbe/mod.rs:458-466`; slot `ProgramState.auto_txn_cleanup` (:856); ARM at successful pre-write COMMIT `core/vdbe/execute.rs:4937` (`op_auto_commit`, TxOp::Commit arm after deferred-FK check); re-arming on every statement start (:2107 reset → :4359/:4442/:4557/:4598 re-arm; :4596 comment: a dropped-statement client that may still call COMMIT explicitly must NOT get cleanup armed); sibling-aware gate `ProgramState::can_autocommit_now(&conn, self_counted)` `core/vdbe/mod.rs:1156-1213`; teardown consumption in `halt()` error paths + vacuum cleanup `core/vdbe/execute.rs:18579-18583`.
**Signature:** `pub(crate) fn can_autocommit_now(&self, connection: &Connection, self_counted: bool) -> bool`.
**Data Shape:** decision inputs = `commit_state != Ready` (already committing ⇒ true), `n_active_writes ∈ {0,1}` assert, MVCC branch (single connection-level tx id), `n_active_root_statements` vs `self_counted`, attached-pager lock probes.

### Decisive source
```rust
// execute.rs:4928-4938 — the new arm (upstream fix c37d1db39):
check_deferred_fk_on_commit(&conn)?;
conn.auto_commit.store(true, Ordering::SeqCst);
state.auto_txn_cleanup = TxnCleanup::RollbackTxn;
// mod.rs:1180-1186 — why the baton matters when the writer dies mid-commit:
if self.auto_txn_cleanup == TxnCleanup::RollbackTxn && self.is_active_write {
    // Pager/WAL writers can finish while sibling readers remain
    // active, like SQLite commits when the halting statement is the
    // only writer (the nVdbeWrite check in sqlite3VdbeHalt)...
    return true;
}
```

**Flow:** explicit `BEGIN; INSERT; COMMIT` → COMMIT's `op_auto_commit` flips autocommit on and arms `RollbackTxn` → commit machine runs (`commit_txn_wal` → `step_end_write_txn` → `pager.commit_tx`, IO-yieldable via `CommitState::{Committing, CommittingAttached}` re-entry). If the WAL pwrite faults mid-commit, the error propagates out of the step; `halt()` sees armed cleanup and rolls the transaction back instead of leaving half-published frames. If the statement is instead RESET/DROPPED while parked (e.g. inside the post-commit auto-checkpoint), teardown consults `can_autocommit_now`: `self_counted=false` means every counted statement is a SIBLING, so a suspended sibling's transaction is never torn down by someone else's drop. Vacuum/VACUUM INTO rides the same baton: it opens a manual BEGIN, arms `RollbackTxn`, and its cleanup funnel rolls back only if still armed.
**Invariant:** arming happens ONLY after all pre-commit validation passed (poison gate + deferred-FK check) — an armed-but-unvalidated COMMIT would let teardown roll back a transaction that could have been fixed. The baton is per-statement and re-evaluated with sibling counts at every teardown point: writer-may-finish-while-readers-remain (WAL branch above) vs last-statement-finishes-attached-leftovers (`can_autocommit_now` tail). Before this upstream change a failed COMMIT left rows visible to a fresh reader of ANOTHER connection ("resurrected rows") because nothing owned the rollback.
**Probe:** fault-injection regression `testing/simulator/runner/io.rs:201 explicit_commit_immediate_pwritev_error_does_not_resurrect_rows` (SimulatorIO injects pwrite fault on the `-wal` file; asserts COMMIT returns the fault, `get_auto_commit()` true, writer AND observer see zero rows, next BEGIN/INSERT/COMMIT succeeds). Text anchors: `grep -c 'state.auto_txn_cleanup = TxnCleanup::RollbackTxn' core/vdbe/execute.rs` ≥ 7; `grep -c 'pub(crate) fn can_autocommit_now' core/vdbe/mod.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "auto_txn_cleanup can_autocommit_now op_auto_commit", limit: 10 });
// resolves ProgramState::can_autocommit_now core/vdbe/mod.rs ~1156-1213
```

## Verdict
Adopt the armed-baton shape for any VM whose COMMIT spans resumable IO: flip the public flag first, arm a private "owns the outcome" token second, let teardown honor the token through sibling-aware gating. Adapt the sibling-count plumbing to your executor model. Omit the MVCC single-tx-id branch unless your store keeps one connection-wide tx. Coverage caveat: none material — the upstream simulator test drives the real fault path.
