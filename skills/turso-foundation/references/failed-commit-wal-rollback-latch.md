<!-- capsule-v2 -->
# Failed COMMIT WAL-write rollback — why must a failed commit arm the rollback latch?

**Source:** turso (Limbo) MIT `main@1654d1587`; Codebase Memory project `turso`. **Question:** After `COMMIT` fails because a WAL write faulted, what state must hold so the transaction is rolled back — not resurrected on a later statement?

## auto_txn_cleanup = RollbackTxn after the auto_commit flip
**Path/Symbol:** `core/vdbe/execute.rs::op_auto_commit` (:4810): TxOp::Commit arm sets `state.auto_txn_cleanup = TxnCleanup::RollbackTxn` at :4937 immediately after `conn.auto_commit.store(true)` (:4936) and after deferred-FK pre-check (:4935); latch type `enum TxnCleanup { None, RollbackTxn, RollbackSavepoint }` (`core/vdbe/mod.rs:458-465`); drop/reset cleanup consumer gate `core/vdbe/mod.rs:2891-2901`; regression `testing/simulator/runner/io.rs::explicit_commit_immediate_pwritev_error_does_not_resurrect_rows` (:201-260) with fault injector `inject_fault_selective` (:71) and `FAULT_ERROR_MSG = "Injected Fault"` (`runner/mod.rs:13`). Commits c37d1db39 (fix) + 5baf4c12a (test).
**Signature:** one-line fix; semantics ride on `ProgramState::auto_txn_cleanup` consulted when a statement is later reset/dropped mid-flight.
**Data Shape:** explicit tx: auto_commit=false while open. The failed COMMIT has already flipped auto_commit=true BEFORE the WAL error unwinds — without the cleanup latch every subsequent reset/drop would see "no transaction" and skip rollback.

### Decisive source
```rust
// core/vdbe/execute.rs:4932-4937 — ordering IS the fix:
//   check_deferred_fk_on_commit(&conn)?;
//   conn.auto_commit.store(true, Ordering::SeqCct);   // (SeqCst)
//   state.auto_txn_cleanup = TxnCleanup::RollbackTxn; // ← NEW: failed write ⇒ roll back
// Regression asserts, io.rs :237-259:
//   commit_result == InternalError(FAULT_ERROR_MSG);
//   wal_file.nr_pwrite_faults incremented by exactly 1;
//   writer.get_auto_commit() == true;  // "the failed COMMIT must end the explicit transaction"
//   query_ids(writer) == query_ids(observer) == []; // "must not retain changes"
```

**Flow:** BEGIN → INSERT buffers via WAL frames → COMMIT drives WAL writes → injected pwritev fault fails submission → op_auto_commit errors out AFTER flipping auto-commit but WITH RollbackTxn armed → statement teardown reads the latch and rolls the whole transaction back → reader/writer both observe empty table (rows not resurrected).
**Invariant:** a failed COMMIT still ENDS the transaction (auto-commit true) but its durability outcome is "nothing persisted"; therefore any post-failure statement teardown must find an armed rollback latch or partial frames leak into later commits as zombie rows. Arm the latch in the same breath as the auto-commit flip — never leave a window where auto-commit is true with cleanup None.
**Probe:** from repo root: `grep -c 'state.auto_txn_cleanup = TxnCleanup::RollbackTxn;' core/vdbe/execute.rs` → count ≥ 9 total arms (:4359/:4442/:4557/:4598/:4937 + others) — assert ≥1 inside the Commit arm by `sed -n '4930,4938p' core/vdbe/execute.rs | grep -c 'RollbackTxn'` → 1. Runner: `TMPDIR=<writable> cargo test -p limbo_sim --bins -- explicit_commit_immediate_pwritev` → 1 passed (executed GREEN ×2 at this pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "op_auto_commit", limit: 3 });
```
(rank-1 resolves `core.vdbe.execute.op_auto_commit` at this pin)

## Verdict
Adopt latch-arming beside the autocommit flip for any engine whose commit can fail after side effects are buffered; adapt to your txn-state enum; omit the simulator fault plumbing (use your own injection harness). Coverage caveat: none material.
