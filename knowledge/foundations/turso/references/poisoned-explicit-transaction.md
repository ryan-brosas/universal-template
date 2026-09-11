<!-- capsule-v2 -->
# Poisoned explicit transaction — why can COMMIT be refused after a writer was dropped mid-statement?

**Source:** turso (Limbo) MIT `main@1654d1587` (re-pinned pass 15 from `def9a060`); Codebase Memory project `turso`. **Question:** When must the engine poison an explicit transaction because no statement savepoint exists to undo a partial write?

## Connection poisoned_tx + Halt poison gate
**Path/Symbol:** `core/connection.rs` — `poisoned_tx: AtomicBool` (:387), `mark_tx_poisoned` (:2809-2811), `tx_is_poisoned` (:2814-2816), `clear_tx_poison` (:2819-2821; called after BEGIN/COMMIT arms at execute.rs :4857 and :5010); poison gate in `core/vdbe/mod.rs:2891-2901`; COMMIT refusal + full rollback in `core/vdbe/execute.rs:4922-4932`.
**Signature:** `pub(crate) fn mark_tx_poisoned(&self)` / `pub(crate) fn tx_is_poisoned(&self) -> bool` / `pub(crate) fn clear_tx_poison(&self)`; gate: `let poison_tx = unfinished_statement_reset_or_drop && inside_explicit_transaction && unfinished_writer && !can_rollback_just_this_statement;`
**Data Shape:** `unfinished_statement_reset_or_drop = err.is_none() && state.execution_state.is_running()` — i.e. the statement is being reset/dropped WITHOUT an error having driven it to completion.

### Decisive source
```rust
// core/vdbe/mod.rs:2896-2901 — the motivating example, verbatim
// Example: BEGIN; UPDATE rows SET ... writes one row, then
// returns IO before reaching Done. If the caller drops that
// statement, we cannot pretend COMMIT is still safe: there is
// no statement savepoint to undo only the partial UPDATE.
self.connection.mark_tx_poisoned();
// core/vdbe/execute.rs:4931 — COMMIT refuses with exact message:
"cannot commit - an unfinished write statement was abandoned"
```

**Flow:** statement dropped/reset while still Running inside an explicit tx AND it was an active writer AND its cleanup mode is not `TxnCleanup::RollbackSavepoint` (which could undo just this statement) → poison flag set → later `COMMIT` sees `conn.tx_is_poisoned()`, runs `rollback_manual_txn_cleanup(pager, true)` (rolls the WHOLE tx back; helper at connection.rs :5134) and returns the TxError above → only BEGIN/COMMIT/ROLLBACK boundaries clear the flag.
**Invariant:** poisoning is conservative in exactly one direction — it fires when there is NO per-statement undo path for partial writes of a live writer. A statement that DID open a statement savepoint (`RollbackSavepoint` cleanup) never poisons. ROLLBACK clears poison so the connection remains usable (test :1230 proves a follow-up INSERT works). Related but distinct: MVCC shared autocommit writers changed rows while a sibling reader held the tx open → forced full rollback (`changed_shared_mvcc_auto_txn`, mod.rs :2905-2912) — same "no statement savepoint" reasoning.
**Probe:** `core/vdbe/statement_lifecycle_tests.rs::test_mvcc_explicit_tx_unfinished_writer_poisons_transaction` (:1165), `test_wal_explicit_tx_unfinished_writer_poisons_transaction` (:1202), `test_explicit_tx_rollback_clears_unfinished_writer_poison` (:1230) — line numbers UNCHANGED by this wave and all three EXECUTED GREEN via `cargo test -p turso_core --features json --lib -- unfinished_writer_poisons rollback_clears_unfinished_writer_poison` → 3 passed (pass 15, first real-runner execution of this trio). Text anchors: `grep -c 'let poison_tx' core/vdbe/mod.rs` → 1; `grep -c 'fn mark_tx_poisoned' core/connection.rs` → 1; `grep -c 'unfinished write statement was abandoned' core/vdbe/execute.rs` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "mark_tx_poisoned unfinished writer", limit: 10 });
```

## Verdict
Adopt the four-condition poison gate and the refuse-COMMIT-then-rollback-whole-tx behavior with the stable error string; adapt flag placement to your connection struct; omit the MVCC sibling-reader variant unless porting shared autocommit transactions.
