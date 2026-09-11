<!-- capsule-v2 -->
# Savepoint name normalization + BUSY gate — where do case-insensitive savepoint names come from, and why do ALL THREE ops reject under suspended writers?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Why does `ROLLBACK TO spcase` find a savepoint registered as `SpCase`, and what is the exact rule deciding when SAVEPOINT/RELEASE/ROLLBACK TO return SQLITE_BUSY-class errors?

## Translate-time ASCII lowercasing (the ONLY normalization site)
**Path/Symbol:** `core/translate/rollback.rs:translate_savepoint/translate_release/translate_rollback` (:11-47); consumed by `op_savepoint` name matching (`core/vdbe/execute.rs` :4868-4870/:4883-4885 rposition comparators).
**Signature:** `program.emit_insn(Insn::Savepoint { op: SavepointOp::Begin, name: name.as_str().to_ascii_lowercase() })`.
**Data Shape:** the Insn carries the ALREADY-lowercased name; every downstream ledger — connection frames, MVCC store named-savepoints, pager `SavepointKind::Named { name }`, mirror calls — keys on the lowercase form. No runtime re-normalization exists anywhere below translate.

### Decisive source
```rust
// core/translate/rollback.rs :34-38
if let Some(savepoint_name) = savepoint_name {
    program.emit_insn(Insn::Savepoint {
        op: SavepointOp::RollbackTo,
        name: savepoint_name.as_str().to_ascii_lowercase(),
    });
}
```

**Flow:** parser yields `ast::Name` verbatim → all three translate functions lowercase with `to_ascii_lowercase()` → opcode handlers match names byte-exactly against ledgers. Consequence: non-ASCII identifiers are NOT folded (ASCII-only, mirroring SQLite's sqlite3UpperToLower ASCII range behavior for savepoint comparison) and any NEW consumer that registers or resolves savepoint names must receive the translated form or lookups silently miss.
**Invariant:** Normalization happens EXACTLY ONCE at translate time; adding a second fold (or none) in engine code creates split-brain registries between paths that received pre-translated names and those that did not.
**Probe:** `grep -c 'to_ascii_lowercase()' core/translate/rollback.rs` = 3 (one per op) and `grep -c 'rposition(|savepoint| savepoint.name == name' core/connection.rs` = 2 (byte-exact comparisons downstream). Direct test: savepoint.sqltest `savepoint-rollback-to-can-be-repeated` family + `savepoint-case-insensitive-name-resolution` (`SAVEPOINT SpCase` / `ROLLBACK TO spcase` / `RELEASE SPCASE` → 2).

## The BUSY gate: one rule for three ops, no cursor-tripping
**Path/Symbol:** `core/vdbe/execute.rs:op_savepoint` prologue (:4760-4776).
**Signature:** gate runs before ANY op-specific work: `if !conn.is_nested_stmt() && conn.n_active_writes.load(Ordering::SeqCst) > 0`.
**Data Shape:** error variant `LimboError::StatementsInProgress(op-specific message)` — "cannot open savepoint" / "cannot release savepoint" / "cannot rollback savepoint".

### Decisive source (the divergence from SQLite, stated in-source)
```rust
// execute.rs :4760-4769
// SQLite rejects SAVEPOINT and RELEASE with SQLITE_BUSY while write
// statements are in progress (vdbe.c, OP_Savepoint: "cannot open/release
// savepoint - SQL statements in progress"). SQLite does allow ROLLBACK TO
// there because it trips all open cursors so the affected statements abort
// instead of resuming; Turso has no cursor-tripping mechanism, and letting
// a suspended writer resume on top of pages restored by ROLLBACK TO would
// interleave two inconsistent page states. Rejecting all three keeps the
// rule simple: finish or reset the active writer first.
```

**Flow:** nested statements bypass the gate entirely (parent owns tx discipline) → otherwise any nonzero active-writer count rejects all three savepoint ops with the per-op message. This deliberately trades SQLite's finer-grained allowance (ROLLBACK TO permitted because SQLite can trip cursors) for simplicity: Turso cannot abort-and-invalidate a suspended writer mid-program, so restored pages would be observed by a writer resuming over TWO different page states.
**Invariant:** A porter whose engine CAN trip cursors may adopt SQLite's asymmetry, but must not half-port it: allowing ROLLBACK TO without cursor tripping corrupts any suspended statement touching rolled-back pages. Nested-statement exemption exists because trigger/subprogram execution shares the parent's writer state.
**Probe:** `sed -n '4760,4776p' core/vdbe/execute.rs | grep -c 'n_active_writes.load(Ordering::SeqCst) > 0'` = 1 and `grep -c 'StatementsInProgress' core/vdbe/execute.rs` ≥ 1 within the op_savepoint prologue; behavioral coverage via tests/fuzz/savepoint.rs outcome-mismatch harness (limbo vs rusqlite must agree Ok-or-Err per statement).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "translate_savepoint SavepointOp to_ascii_lowercase", limit: 5 });
// turso.core.translate.rollback.translate_savepoint Function core/translate/rollback.rs 11-17
```
Verified live at pin def9a060 (line-exact); check_index_coverage on core/translate/rollback.rs = no_recorded_issue + metadata_match.

## Verdict
Adopt single-site translate-time ASCII lowercasing as the contract for every savepoint-name registry, and the conservative reject-all-three BUSY gate whenever the host lacks cursor tripping. Adapt message strings/error variants to host taxonomy. Omit nothing — both behaviors are small, load-bearing, and directly test-pinned (savepoint.sqltest case-insensitivity test; differential fuzz outcome-parity harness).
