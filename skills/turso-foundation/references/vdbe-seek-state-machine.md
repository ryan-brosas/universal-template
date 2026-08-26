<!-- capsule-v2 -->
# VDBE seek state machine — how does one bytecode instruction survive being interrupted by async IO mid-seek, and what does it do about floats that aren't valid rowids?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** Where does a SeekGE/SeekGT/SeekLE/SeekLT opcode keep its progress across IO yields, and how are affinity/precision edge cases folded into the op BEFORE the cursor is touched?

## Four-state resume machine in ProgramState + outer non-IO reset

**Path/Symbol:** `core/vdbe/execute.rs` — `OpSeekState { Start, Seek{key,op}, Advance{op}, MoveLast }` :5713-5723 (stored as `state.seek_state` on `ProgramState`), `seek_internal` :5855-6158 with inner loop :5876-6141, reset-on-non-IO :6154-6156, `SeekInternalResult::{Found,NotFound,IO}` :5836-5840, entry `op_seek` :5725-5833 (NULL-key short-circuit :5770-5797), float/text precision rewrite :5928-6000.
**Signature:** `pub fn seek_internal(program, state, pager, record_source: RecordSource, cursor_id: usize, is_index: bool, op: SeekOp) -> Result<SeekInternalResult>`.
**Data Shape:** `OpSeekKey::{TableRowId(i64), IndexKeyFromRegister(reg), IndexKeyUnpacked{start_reg,num_regs}}`; per-op metrics (`btree_seeks`, `search_count`) bumped at each real cursor action.

### Decisive source
```rust
// execute.rs:6069-6072 — the yield seam inside Seek:
SeekResult::TryAdvance => {
    state.seek_state = OpSeekState::Advance { op: *op };
    continue;   // next call resumes INSIDE the loop at the new arm
}
// execute.rs:6154-6156 — the lifecycle rule:
if !matches!(result, Ok(SeekInternalResult::IO(..))) {
    state.seek_state = OpSeekState::Start;
}
```
Every cursor interaction returns `IOResult::{Done, IO}`; on IO the function returns immediately and the ENTIRE instruction re-executes later, but the match dispatches on the persisted `state.seek_state` instead of starting over. `Advance` exists because b-tree seeks can land on a leaf whose divider promised candidates but holds none (:6084-6102 comment with the `[> 666]` / P1[661,665] example) — then `next()`/`prev()` walks to the neighbor leaf, deliberately via `get_next_record()`-style calls that bypass skip_advance (:6107-6111).

**Flow (table-btree Start arm):** unpack register → apply numeric affinity to text → `extract_int_value`; if conversion failed or precision lost, REWRITE THE OP before seeking: float beyond i64 range gets direct comparison logic (`int_key == i64::MAX && f > 9223372036854774784.0 ⇒ -1` etc. :5930-5966); `(x < 5.1) → (x <= 5)`, `(x >= 5.1) → (x > 5)`, `(x > 4.9) → (x >= 5)` (:5970-5977). Non-numeric text vs integer: GT/GE return NotFound ("no integers > text"), LT/LE transition to `MoveLast` ("all integers < text" :5982-5995). NULL key ⇒ NotFound for all ops (:6001-6010). Only THEN does `Seek` touch the cursor.

**Invariant:** state transitions happen ONLY in `ProgramState`, never in locals — any refactor that caches "current phase" in a stack local breaks resume-after-IO. The outer reset fires on EVERY terminal result (Found/NotFound/Err), so a stale machine can never leak into the next invocation of the same opcode slot. MoveLast must still answer NotFound on an empty table or the scan emits one garbage row (:6130-6138).

**Probe:** behavior is pinned end-to-end by conformance suites exercising seek semantics under injected IO (the same resume protocol is unit-tested via `testing-yield-injection`'s cfg-gated YieldPoints for MVCC machines; b-tree side via hermitage/sqllogictest runs). No cargo runner in this clone — verified by direct source inspection at `def9a060`; coverage caveat: no dedicated Rust unit test names `OpSeekState` directly.

**Retrieve:**
```
echo '{"project":"turso","query":"OpSeekState seek_internal","limit":5}' | codebase-memory-mcp cli search_graph
# turso.core.vdbe.execute.seek_internal execute.rs 5855-6158
# turso.core.vdbe.execute.OpSeekState execute.rs 5713-5723
```

## Verdict
Adopt the persisted-state-machine-per-opcode pattern (state lives on ProgramState, reset on every non-IO exit) for ANY async-stepped VM instruction — this generalizes `vdbe-async-step-loop`'s three-channel protocol to individual opcodes. Adopt the op-rewrite-before-seek discipline for cross-type range comparisons. The deferred index→table lookup variant of the same pattern is `OpColumnState` (Start→Rowid→Seek→GetColumn, execute.rs:1770-1985).
