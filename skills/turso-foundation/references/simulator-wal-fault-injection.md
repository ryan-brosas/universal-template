<!-- capsule-v2 -->
# Simulator WAL fault injection harness — how do you test "commit failed mid-write" deterministically?

**Source:** turso (Limbo) MIT `main@1654d1587`; Codebase Memory project `turso`. **Question:** How does the simulator make an IO fault land on exactly the WAL write inside COMMIT, and what assertions pin the observable contract?

## Selective per-file fault arming around a single statement
**Path/Symbol:** `testing/simulator/runner/io.rs`: `SimulatorIO::new(1, 4096, 0, 1, 1, IoBackend::Default)` (test :206), `inject_fault_selective(&[(&wal_path, bool)])` (:71), fault counter `nr_pwrite_faults: Cell<usize>` (:137), shared file registry `io.files.borrow().iter().find(|f| f.path == wal_path)` (:219-224); message constant `FAULT_ERROR_MSG = "Injected Fault"` (`testing/simulator/runner/mod.rs:13`); full regression `explicit_commit_immediate_pwritev_error_does_not_resurrect_rows` (:201-260) using core APIs `Connection::execute`, `get_auto_commit` (core/connection.rs:2801), `Statement::run_with_row_callback` (core/statement.rs:781). Commit 5baf4c12a.
**Signature:** `fn inject_fault_selective(&self, faults: &[(&str, bool)])` — path-keyed arm/disarm, so faults hit ONLY writes to that file while armed.
**Data Shape:** assertion tuple after the faulted COMMIT: `Err(LimboError::InternalError(m)) if m == FAULT_ERROR_MSG`; `nr_pwrite_faults == before + 1` proves the failure came from the armed WAL pwritev.

### Decisive source
```rust
// io.rs:228-233 — arm → act → disarm, one statement wide:
//   io.inject_fault_selective(&[(&wal_path, true)]);
//   let commit_result = writer.execute("COMMIT");
//   io.inject_fault_selective(&[(&wal_path, false)]);
```

Then the contract triple: auto-commit flag is TRUE post-failure (`writer.get_auto_commit()` — failed COMMIT ends the tx), writer's own view empty AND observer's view empty (`query_ids` helper :190-198 drives SELECT via run_with_row_callback) — nothing resurrected on either connection.
**Invariant:** fault tests must COUNT their faults (counter +1) or a spurious unrelated failure satisfies the assert; scope faults by FILE PATH + boolean window so background IO cannot absorb the blame; observe through a SECOND connection to prove durability boundaries, not just local cache effects.
**Probe:** from repo root: `grep -c 'fn inject_fault_selective' testing/simulator/runner/io.rs` → 1; `grep -c 'FAULT_ERROR_MSG' testing/simulator/runner/mod.rs` → 1; runner: `TMPDIR=<writable> cargo test -p limbo_sim --bins -- explicit_commit_immediate_pwritev` → 1 passed (executed GREEN ×2 at this pin; package is bin-only: pass `--bins`, NOT `--lib`). Environment caveat recorded: default TMPDIR (/tmp quota) RED'd the C-binding twins this wave; always give tempfile-based suites a writable TMPDIR.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "inject_fault_selective", limit: 3 });
```
(resolves the io.rs fn node line-exact at this pin)

## Verdict
Adopt path-scoped arm/act/disarm fault windows plus a fault counter for any storage-engine test rig; adapt injection points to your VFS seam; omit the two-connection observer only if you have an equivalent external witness. Coverage caveat: none material.
