<!-- capsule-v2 -->
# C-API completion contract — why must finalize/reset run to completion but NEVER leak the statement?

**Source:** turso (Limbo) MIT `main@1654d1587`; Codebase Memory project `turso`. **Question:** What do sqlite3_finalize / sqlite3_reset return when the pending execution cannot finish, and what is the one thing they must still guarantee?

## Report the error, free/reset anyway
**Path/Symbol:** `bindings/c/src/lib.rs`: `stmt_run_to_completion` (:1028-1037), `sqlite3_finalize` (:1040, early-return removed — now falls through to `Box::from_raw(stmt)` and returns `result` at :1077), `sqlite3_reset` (:1403, reset error swallowed when completion already failed :1412-1416, returns `result` :1419); NULL-statement SQL special case in `sqlite3_prepare_v2` (:966-980 matching SQLite c3ref/prepare: empty/whitespace/comment-only SQL ⇒ SQLITE_OK + *ppStmt=NULL + tail=end); direct tests `test_finalize_frees_statement_stuck_on_busy` (:3721) / `test_reset_resets_statement_stuck_on_busy` (:3752) with fixture `prepare_statement_stuck_on_busy` (:3785). Commit 27c3bccb0.
**Signature:** `unsafe fn stmt_run_to_completion(stmt: *mut sqlite3_stmt) -> ffi::c_int` — steps until running==false, returning first non-DONE/ROW code.
**Data Shape:** a statement stuck on SQLITE_BUSY still occupies an active-root-statement slot on its connection until finalize runs the unregister block (:1048-1060).

### Decisive source
```rust
// lib.rs test comment :3712-3719 — the failure mode verbatim:
//   Returning early instead leaked the statement and left it counted as an
//   active root statement on the connection forever, so every later "no
//   statements active" check failed — an explicit checkpoint always errored
//   and DETACH reported the database locked.
// Post-fix ordering (finalize): result = stmt_run_to_completion(...);
//   ...unregister from db stmt_list...; let _ = Box::from_raw(stmt); result
// reset: if reset() errs AND result == SQLITE_OK → surface reset error; else
//   prev_search_count = 0; clear_text_cache(); return result  // BUSY wins
```

**Flow:** step hits BUSY while another connection holds the write lock → user calls finalize/reset → run-to-completion re-attempts and fails again (that IS the reported code) → finalize frees memory + unregisters regardless; reset clears state so the SAME statement re-runs from the start once the lock clears (test asserts sqlite3_step ⇒ SQLITE_DONE afterwards).
**Invariant:** finalize/reset are destructor-like for RESOURCE purposes: their return code reports the last evaluation error, but no error path may skip freeing/unregistering. Conversely prepare of statement-free SQL is SUCCESS-with-NULL, not an error — core's InvalidArgument("The supplied SQL string contains no statements") must be translated at the FFI boundary only.
**Probe:** from repo root: `grep -n -A4 'let result = stmt_run_to_completion' bindings/c/src/lib.rs | grep -c 'return result'` → 1 (finalize tail); `grep -c 'The supplied SQL string contains no statements' bindings/c/src/lib.rs` → 1. Runner: `TMPDIR=<writable> cargo test -p turso_sqlite3 --lib -- stuck_on_busy` → 2 passed (executed GREEN at this pin; RED under default TMPDIR was the host /tmp quota defect, not source).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "stmt_run_to_completion", limit: 3 });
```
(rank-1 resolves bindings/c/src/lib.rs 1028-1037 line-exact after this pass's re-index)

## Verdict
Adopt report-error-but-free-anywhere semantics plus OK+NULL for nothing-to-compile verbatim in any C-compatible wrapper; adapt error mapping to your core error enum; omit busy fixtures if your locking model cannot produce mid-execution BUSY. Coverage caveat: none material.
