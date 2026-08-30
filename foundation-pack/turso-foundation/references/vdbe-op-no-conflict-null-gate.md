<!-- capsule-v2 -->
# op_no_conflict null short-circuit — why does any NULL in the probe record mean "no unique conflict" before touching the index?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** What lets a uniqueness pre-check skip the seek entirely, and what must the two-state machine remember across its IO?

## NULL-in-record ⇒ unconditional jump; else one eq-only GE seek decides
**Path/Symbol:** `core/vdbe/execute.rs`: `enum OpNoConflictState` (:12537-12541: `Start | Seeking(RecordSource)`), `op_no_conflict` (:12545-12630); shared machinery `seek_internal` + `SeekInternalResult::{Found, NotFound, IO}`; SQL semantics doc at :12543.
**Signature:** insn `NoConflict { cursor_id, target_pc, record_reg, num_regs }`; decision: `SeekOp::GE { eq_only: true }` with `eq_only=true` — Found ⇒ fall through (conflict), NotFound ⇒ jump `target_pc`.
**Data Shape:** `RecordSource::{Packed{record_reg} | Unpacked{start_reg, num_regs}}` chosen by `num_regs == 0`; the source is carried INSIDE the `Seeking` state so resume needs no re-derivation.

### Decisive source
```rust
// execute.rs:12575-12596 (condensed):
//   // If there is at least one NULL in the index record, there cannot be a conflict
//   // so we can immediately jump.
//   let contains_nulls = match &record_source {
//       RecordSource::Packed { record_reg } =>
//           record.iter()?.any(|val| matches!(val, Ok(ValueRef::Null))),
//       RecordSource::Unpacked { start_reg, num_regs } =>
//           (0..*num_regs).any(|i| matches!(&state.registers[start_reg+i],
//                                          Register::Value(Value::Null))),
//   };
//   if contains_nulls { state.pc = target_pc…; return … }        // no seek at all
// :12613-12624 — inverted polarity vs the opcode name:
//   SeekInternalResult::Found    => { state.pc += 1; …  }         // conflict → continue
//   SeekInternalResult::NotFound => { state.pc = target_pc…; }    // "no conflict" → jump
```
The jump-on-NULL rule is SQL's UNIQUE semantics (NULLs never collide), applied BEFORE the async seek so the common partial-null insert costs zero IO. The polarity trap: this opcode jumps when the row is ABSENT — opposite of most seek opcodes — and it delegates all cursor positioning to `seek_internal`, reusing the MVCC/B-tree-aware ladder rather than duplicating it.

**Flow:** Start → classify RecordSource → scan for NULLs (packed iter or register window) → any NULL ⇒ clear slot, pc=target_pc → else enter Seeking(source) → `seek_internal` eq-only GE → IO propagates out for resume-at-same-arm → Found/NotFound set fall-through/jump respectively and clear the slot.

**Invariant:** the NULL check precedes ANY IO; the RecordSource travels inside the state machine so an IO yield cannot desync which registers hold the probe key.

**Probe:** structural pins at HEAD via search_graph (`OpTransactionState` resolves execute.rs:3736-3742; NoConflict machine read whole :12537-12630). Coverage caveat: upstream pins uniqueness behavior in conformance suites rather than a unit test named for this opcode; deterministic source checks stand in here (no cargo runner in the inspo clone).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "op_no_conflict OpNoConflictState RecordSource seek_internal SeekInternalResult", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the NULL-before-seek short-circuit and the inverted jump polarity for any unique-constraint pre-check. Adapt RecordSource to your register model. Omit nothing if you port SQLite-style uniqueness enforcement. Coverage caveat recorded above.
