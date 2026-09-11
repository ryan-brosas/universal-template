<!-- capsule-v2 -->
# VDBE active-op slot — how does ONE suspended-opcode slot serve every resumable opcode without cross-contamination?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** Many opcodes need to suspend mid-operation on async IO, but the program keeps a single op-state — what discipline makes that safe?

## One enum slot + typed accessors that lazy-init and hard-panic on mismatch
**Path/Symbol:** `core/vdbe/mod.rs`: `ActiveOpState` enum (20 payload variants incl. `Delete/ClearBtree/Destroy/IdxDelete/IdxInsert/NoConflict/NewRowid/Column/RowId/Transaction/Attach/JournalMode/ParseSchema/Program`, Debug names :552-573), `struct ActiveOpStateSlot` (:578-581), macro `active_state_accessor!` (:583-599), `clear()` (:607-609)/`is_idle()` (:613-616), accessor instantiations :625+.
**Signature:** `fn $name(&mut self) -> &mut $ty { if matches!(self.state, ActiveOpState::None) { self.state = ActiveOpState::$variant($init) } … else unreachable!("active opcode state mismatch: expected {}, got {:?}", …) }`; `fn is_idle(&self) -> bool { matches!(self.state, ActiveOpState::None) }`.
**Data Shape:** `ActiveOpState::None | Transaction(OpTransactionState) | NewRowid(OpNewRowidState) | Column(OpColumnState) | …` — exactly ONE opcode may be suspended per program; each variant carries its own machine's payload (counters, candidates, cursor ids).

### Decisive source
```rust
// mod.rs:583-598 — accessor contract:
//   if matches!(self.state, ActiveOpState::None) {
//       self.state = ActiveOpState::$variant($init);
//   }
//   match &mut self.state {
//       ActiveOpState::$variant(state) => state,
//       state => unreachable!(
//           "active opcode state mismatch: expected {}, got {:?}",
//           stringify!($variant), state
//       ),
//   }
// mod.rs:612-613 — hot-path bypass:
//   /// True when no multi-step opcode is suspended. Hot opcodes use this to
//   /// bypass the slot entirely on their non-yielding fast path.
```
The mismatch panic is load-bearing: two interleaved multi-step opcodes sharing the single slot would silently corrupt each other's payloads; failing loudly turns a scheduling bug into an immediate diagnostic.

**Flow:** opcode entry → fast-path check `is_idle()` (op_column :1899 "no deferred seek pending and no suspended state machine … re-executes") → slow path takes typed accessor (lazy-inits variant) → loop over machine states, every IO yield returns with progress persisted in the slot → terminal arm sets pc+=1 then `clear()` back to None → next opcode may claim it. Error paths clear explicitly (e.g. op_transaction wrapper :3773-3779 `state.active_op_state.clear()`).

**Invariant:** at most one suspended opcode per program; an opcode claiming the slot while another's machine is live panics; every exit path (success, error) clears or leaves a coherent machine for exact resume-at-same-PC semantics.

**Probe:** structural pins read directly at HEAD: `turso.core.vdbe.mod.ActiveOpStateSlot.clear` resolves via search_graph (`core/vdbe/mod.rs 608-610`); resume behavior pinned by `test_mvcc_cursor_next_yields_with_injected_yield` (`core/mvcc/database/tests.rs:6031-6075`, cited by mvcc-lazy-cursor.md). Coverage caveat: no cargo runner in inspo clone; deterministic source checks stand in for execution.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "ActiveOpStateSlot active_state_accessor ProgramState active_op_state is_idle", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one-slot-per-program suspension ONLY if your executor guarantees a single in-flight suspendable opcode; otherwise generalize to a map keyed by opcode/cursor. Adapt the macro to your language's pattern-matching idioms. Omit the debug-name plumbing if you lack structured logging. Coverage caveat recorded above.
