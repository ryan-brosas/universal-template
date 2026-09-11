<!-- capsule-v2 -->
# Checkpoint IO-error cleanup ledger — how do you unwind a half-finished MVCC checkpoint without wedging the database?

**Source:** turso MIT `main@def9a0601b8ead82675e672e1843447251b15fb4`; Codebase Memory `turso`. **Question:** When a checkpoint fails mid-flight (IO error outside `step()`, statement abort, abandoned journal-mode switch), exactly which resources must be released, in what order, and who owns calling the cleanup?

## LockStates mirror + single mirrored cleanup funnel
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs` — `LockStates` struct :148-152 (`blocking_checkpoint_lock_held`, `pager_read_tx`, `pager_write_tx` — three bools); owner `CheckpointStateMachine::cleanup_after_external_io_error(&mut self, err: LimboError) -> Result<()>` :874-910; shared tail helper `release_checkpoint_locks_if_needed` :857-869 (blocking lock unlock + `mvstore.checkpoint_in_progress.store(false)` when `owns_checkpoint_in_progress`); step()-internal error arm `StateTransition::step` :3019-3027 routes through the SAME function.
**Signature:** `pub fn cleanup_after_external_io_error(&mut self, err: LimboError) -> Result<()>`.
**Data Shape:** Input = the error that killed the run (real `LimboError` from `iocompletions.wait`, or synthetic `InternalError("mvcc: cleanup_unfinished_commit")` / `"mvcc: abandoned journal-mode checkpoint"` when no real error exists). Returns the result of `storage.on_checkpoint_end(Err(err))` — i.e. the DurableStorage end-hook sees the failure even though nothing durable was written by this machine.

### Decisive source
```rust
// :874-910 — order IS the contract:
let result = self.mvstore.storage.on_checkpoint_end(Err(err));
// staged root-map ops were NEVER published (deferred to post-commit publish window)
// => discard, not revert: a post-commit failure finds these already drained.
self.pending_rootmap_ops.clear();
self.pending_alloc_roots.clear();
if self.lock_states.pager_write_tx {
    self.pager.rollback_tx(self.connection.as_ref());
    if self.update_transaction_state {
        self.connection.set_tx_state(TransactionState::None);
    }
    self.lock_states.pager_write_tx = false;
    self.lock_states.pager_read_tx = false;      // write implies read: clear BOTH
} else if self.lock_states.pager_read_tx {
    self.pager.end_read_tx();
    if self.update_transaction_state { /* set_tx_state(None) */ }
    self.lock_states.pager_read_tx = false;
}
self.pager.clear_checkpoint_state();             // pager.rs:4562 phase->NotCheckpointing
if let Some(wal) = self.pager.wal.as_ref() { wal.abort_checkpoint(); } // wal.rs:4136 take guard
self.release_checkpoint_locks_if_needed();
result
```

**Flow:** Six call sites funnel into one body — (1) `step()`'s own error arm :3019-3027 ("cleanup already calls on_checkpoint_end + unlock"); (2) external-IO waits in `Connection::checkpoint` loop `core/connection.rs:2327` and OpCheckpoint `core/vdbe/execute.rs:644` (`iocompletions.wait()` failed while parked outside `step()`) — both then return the original error; (3) commit-machine teardown `CommitStateMachine::cleanup_mvcc_checkpoint_state` `core/mvcc/database/mod.rs:1678-1685` via `cleanup_unfinished_commit` :1728-1730 (guarded by `is_finalized`) — reached from vdbe abort paths `core/vdbe/mod.rs:219/:222/:1039/:2605` (the :2605 comment: MVCC auto-checkpoint is owned by commit_state, so `abort()` is the first cleanup path that still owns it); (4) journal-mode abandonment `OpJournalModeState::cleanup_checkpoint` `core/vdbe/execute.rs:17718-17728` on statement reset/drop.
**Invariant:** The three `LockStates` bools are the ONLY record of what was acquired (acquisition sets them exactly once each: blocking lock :1993-1998 blocking mode / :2719-2723+:2780-2784+:2918-2922 passive publish window; `pager_read_tx` :2138 only when WAL doesn't already hold the read lock; `pager_write_tx` :2149 unconditionally after `begin_write_tx`). Cleanup must be idempotent from ANY state: write-tx arm clears BOTH pager flags (write tx subsumes the read tx); pager/WAL checkpoint bookkeeping resets UNCONDITIONALLY because "MVCC checkpointing drives WAL checkpoint directly" (:902-905 comment) — unlike legacy pager paths there is no outer owner to do it; connection `tx_state` is only reset when `update_transaction_state==true` (auto-checkpoints inside a user transaction leave state to VDBE error handling).
**Probe:** `core/mvcc/database/tests.rs:4102-4107` inside `test_meta_checkpoint_case_11_auto_checkpoint_failure_after_commit_remains_recoverable` (:3935) — drives a checkpoint to `CheckpointWal`, injects `cleanup_after_external_io_error(LimboError::Interrupt)`, then asserts the NEXT checkpoint finishes cleanly and rows survive (`recovery-after-failed-checkpoint` behavior); sibling direct test of the abandonment path: `abandoned_journal_mode_checkpoint_releases_pager_transaction_and_lock` (:2201) asserts post-reset `tx_state == None` AND blocking lock re-acquirable.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "cleanup_after_external_io_error", limit: 10, fields: ["signature", "name", "file"] });
// resolves Method core/mvcc/database/checkpoint_state_machine.rs 874-910
```

## Verdict
Adopt the mirrored-single-funnel shape (one cleanup body, every failure route calls it) and the discard-not-revert rule for staged-but-unpublished mutations; adopt the unconditional pager+WAL checkpoint-state reset as the price of MVCC owning WAL checkpoints directly. Adapt flag names/lock types to your host. Omit nothing silently: dropping the write-subsumes-read double-clear or the `update_transaction_state` guard deadlocks or clobbers user transactions respectively. Coverage caveat: none (all five cited paths `no_recorded_issue`, generation matches).
