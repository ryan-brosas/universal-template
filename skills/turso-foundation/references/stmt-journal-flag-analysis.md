<!-- capsule-v2 -->
# Statement journal flag analysis — which writes need statement-level undo?

**Source:** turso (Limbo) MIT `main@def9a060`; Codebase Memory project `turso`. **Question:** How does Turso decide `usesStmtJournal` (is_multi_write && may_abort) per DML statement without SQLite's runtime cost?

## stmt_journal.rs flag analysis feeding build_prepared_program
**Path/Symbol:** `core/translate/stmt_journal.rs` — `constraint_may_abort` (:81-116), `any_effective_replace` (:44-55), `set_insert_stmt_journal_flags` (:124-192), `set_update_stmt_journal_flags` (:195-267), `set_delete_stmt_journal_flags` (:270-299); consumption in `core/vdbe/builder.rs::build_prepared_program` (:2177-2186) and `may_abort()` (:879-880).
**Signature:** `pub(crate) fn constraint_may_abort(has_statement_conflict: bool, statement_conflict: ResolveType, rowid_alias_conflict: Option<ResolveType>, indexes: impl Iterator<Item = (Option<ResolveType>, bool)>, has_notnull: bool, has_check: bool, has_unique: bool) -> bool`; builder fold: `let needs_stmt_subtransactions = matches!(self.txn_mode, TransactionMode::Write) && self.flags.is_multi_write() && self.may_abort();`
**Data Shape:** both builder flags default `true` (conservative); each DML translate path narrows them. Index input is `(on_conflict, is_unique)` pairs read from the live schema via the Resolver.

### Decisive source
```rust
// core/vdbe/builder.rs:2179 — the contract sentence
// Mirrors SQLite's: usesStmtJournal = isMultiWrite && mayAbort
let needs_stmt_subtransactions = matches!(self.txn_mode, TransactionMode::Write)
    && self.flags.is_multi_write()
    && self.may_abort();
// stmt_journal.rs:160 — AUTOINCREMENT taints may_abort ONLY for multi-row inserts:
// op_sequence_compute_next returns DatabaseFull on i64 exhaustion; a second row
// failing mid-statement must not leak the FIRST row's write past COMMIT.
let autoinc_may_abort_multi_row = has_autoincrement && inserting_multiple_rows;
```

**Flow:** translate INSERT/UPDATE/DELETE → set_*_stmt_journal_flags computes effective resolution per constraint (statement override wins, else DDL mode, else ABORT) → flags stored on ProgramBuilder → `build_prepared_program` folds them (+ any emitted `Insn::Function`, since functions can RAISE at runtime) into an `AtomicBool needs_stmt_subtransactions` on `PreparedProgram`.
**Invariant:** a single-row write is atomic — opt out via `set_multi_write(false)` regardless of abortability. REPLACE resolves UNIQUE conflicts by replacing (never aborts on unique) but still falls back to ABORT for NOT NULL/CHECK. UPSERT `DO UPDATE` always runs ABORT semantics (SQLite hardcodes OE_Abort for the inner UPDATE) so it forces `may_abort` even when `INSERT OR REPLACE` alone would not. DELETE has no ON CONFLICT clause: only triggers (RAISE(ABORT)) or FK violations can abort it.
**Probe:** `tests/integration/stmt_journal.rs::insert_or_replace_upsert_do_update_may_abort` (:688 — same statement with `DO UPDATE SET` needs the journal, `DO NOTHING` does not); text anchors: `grep -c 'usesStmtJournal = isMultiWrite && mayAbort' core/vdbe/builder.rs` → 1; `grep -c 'autoinc_may_abort_multi_row = has_autoincrement && inserting_multiple_rows' core/translate/stmt_journal.rs` → 1; `grep -c 'set_multi_write(false)' core/translate/stmt_journal.rs` → 3.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "statement journal is_multi_write may_abort constraint_may_abort", limit: 10 });
```

## Verdict
Adopt the compile-time flag analysis (isMultiWrite ∧ mayAbort) and the per-constraint effective-resolution ladder; adapt the AtomicBool hand-off to however your VM carries prepared-statement metadata. Omit the fuzz generator tables (`tests/fuzz/subjournal.rs`) unless porting differential testing. Coverage caveat: virtual tables keep conservative defaults (both flags true) — see `set_update_stmt_journal_flags` early return.
