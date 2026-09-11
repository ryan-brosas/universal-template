<!-- capsule-v2 -->
# VDBE column deferred-seek machine — how does an index-column read become a rowid fetch plus a table seek without losing its place across IO yields?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What is the per-opcode state pattern for the hottest instruction in the VM (Column), and where must the slot persist so a resumed step re-enters the same arm?

## Four-arm loop with a sticky GetColumn slot

**Path/Symbol:** `core/vdbe/execute.rs` — `OpColumnState { Start, Rowid{index_cursor_id, table_cursor_id}, Seek{rowid, table_cursor_id}, GetColumn }` :1770-1781; driver `'outer: loop` over `state.active_op_state.column()` :1904-1985 (Start :1908-1922, Rowid :1918-1937, Seek :1938-1963, GetColumn :1964-1973); terminal `state.active_op_state.clear(); state.pc += 1` :1985-1987.
**Signature:** `op_column_impl(program, state, cursor_id, fetch: ColumnFetch)` — one implementation serves both `Column` (single) and `ColumnRange` via `ColumnFetch::{Single, Range}` :1839-1852.
**Data Shape:** deferred seeks are staged in `state.deferred_seeks[cursor_id]` and consumed (`take()`) at Start.

### Decisive source
```rust
// execute.rs:1964-1973 — the sticky-slot rule for mid-fetch yields:
OpColumnState::GetColumn => {
    let result = fetch.fetch(program, state, cursor_id)?;
    if !matches!(result, InsnFunctionStepResult::Step) {
        // IO yield: the slot stays at GetColumn so the resume
        // re-enters this arm.
        return Ok(result);
    }
    break 'outer;
}
```
The machine encodes SQLite's classic index-then-table dance as explicit states: Start consumes a deferred seek (or skips straight to GetColumn when reading a table cursor), Rowid reads the index cursor's current rowid (writing NULLs and exiting if the index has no row), Seek positions the TABLE cursor at that exact rowid with `SeekOp::GE { eq_only: true }`, GetColumn materializes register values. Each arm's cursor calls are `return_if_io!`-wrapped: an IO return leaves the slot pointing at the CURRENT arm, so the next step resumes that arm rather than re-running earlier ones.

**Flow:** Column on index cursor → Start takes deferred_seek → Rowid (index cursor.rowid(), may yield) → Seek (table cursor.seek(rowid, GE eq_only), may yield; bumps btree_seeks/search_count metrics) → GetColumn (fetch into dest reg(s), may yield IN PLACE) → clear slot + pc += 1. MaterializedView cursors get an explicit in-Seek branch (:1946-1951) instead of falling through b-tree logic.

**Invariant:** the state slot is cleared ONLY on the successful terminal path — an error or IO must leave it set, because the opcode will be re-entered from the top of its function on resume. The Seek arm pins `eq_only: true` (exact rowid match); using a range op here would silently skip rows after b-tree splits.

**Probe:** exercised by every conformance suite touching indexed reads (sqlite conformance + sqllogictest in-repo); the resume protocol itself is validated by the yield-injection architecture (`core/mvcc/yield_points.rs`, capsule `testing-yield-injection`). No cargo runner in this clone — verified by direct source inspection at `def9a060`; coverage caveat: no unit test names OpColumnState directly.

**Retrieve:**
```
echo '{"project":"turso","query":"OpColumnState op_column deferred seek","limit":5}' | codebase-memory-mcp cli search_graph
# turso.core.vdbe.execute.op_column / op_column_impl execute.rs 1770-1985
```

## Verdict
Adopt for any VM whose instructions can suspend: one enum per complex opcode, stored on program state, consumed by a match-loop, cleared only at completion. Pair with `vdbe-seek-state-machine` (the SeekGE family's richer four-state cousin) and `vdbe-async-step-loop` (the Program::step protocol that calls into these machines).
