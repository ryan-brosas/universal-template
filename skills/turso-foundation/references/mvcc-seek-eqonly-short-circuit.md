<!-- capsule-v2 -->
# MVCC cursor eq-only seek short-circuit — why does a redundant point-seek mid-range-scan corrupt the delete loop?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** When a caller re-seeks an already-positioned cursor with `eq_only`, why must you return Found without touching either iterator — and what scan dies if you don't?

## Position+visibility check replaces the seek when op.eq_only() and state is idle
**Path/Symbol:** `core/mvcc/cursor.rs`: `MvccLazyCursor::seek` short-circuit (:1543-1574), helper `current_pos_matches_seek_key` (:167-188), the failure-mode comment block (:1516-1542).
**Signature:** gate: `if self.state.is_none() && op.eq_only()`; visibility: `read_from_table_or_index(..).is_some() || (*in_btree && self.query_btree_version_is_valid(&row_id.row_id))`.
**Data Shape:** inputs = current `CursorPosition::Loaded { row_id, in_btree }`, incoming `SeekKey` (TableRowId | IndexKey), `SeekOp.eq_only()`; output = `SeekResult::Found` WITHOUT resetting iterators/peeks, or fall through to the full seek ladder.

### Decisive source
```rust
// cursor.rs:1530-1542 — the documented corruption (abridged):
// 1. we seek to the first matching key using SeekOp::GT { eq_only: false } …
// 2. op_idx_delete forces a eq_only seek on the cursor … the index cursor is
//    already correctly positioned.
// 4. we seek btree_cursor, don't find the row, and set it to Exhausted …
//    EVEN THOUGH the seek from step 1 would still have matched rows in the b-tree.
// 5. eventually, the mvcc cursor runs out … the next Insn::Next INCORRECTLY finds
//    the index cursor exhausted and breaks out of the delete loop, even though
//    there are still b-tree-resident rows to delete.
// :1553-1559 — both visibility cases must short-circuit:
//   The current row is visible either because MvStore has a visible version for it,
//   or because it is a b-tree-resident row that is not shadowed by any MVCC version.
//   Both cases must short-circuit: otherwise a b-tree-only row would fall through to
//   the full eq-only seek below, which resets the iterators and marks the MVCC peek
//   exhausted, skipping MvStore-resident rows that the enclosing range scan still needs to visit.
```
Key-match equality is per key type: `RowKey::Int == TableRowId`, or `compare_immutable(target, current, &key_info).is_eq()` truncated to the seeker's column count for index keys (:172-185).

**Flow:** idle state + eq_only + position matches key → probe visibility (MVCC visible OR unshadowed B-tree row) → clear `null_flag` (outer-join NullRow contamination) → return Found. Any miss (state active, not eq_only, key mismatch, invisible) falls into the full ladder: reset iterators → synchronous MVCC seek primes mvcc_peek → async btree seek machine (`SeekBtreeState::{SeekBtree, AdvanceBTree, CheckRow}`) → `PickWinner` by direction.

**Invariant:** an eq_only seek on a correctly positioned VISIBLE row is a no-op that preserves all dual-peek/iterator state; only non-eq_only or genuinely-missed seeks may reset iteration state.

**Probe:** behavioral surface covered indirectly by upstream delete/index suites exercising `op_idx_delete` over checkpointed tables; the exact regression scenario is pinned by source comment :1516-1560 read at HEAD. Coverage caveat: no dedicated unit test named `*eq_only*short_circuit*` exists at this pin; deterministic needle checks below stand in for execution (no cargo runner available).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "MvccLazyCursor seek eq_only current_pos_matches_seek_key op_idx_delete", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the short-circuit whenever cursors serve BOTH range scans and point operations (SQLite-style OP_IdxDelete/DeferredSeek patterns); it is what makes redundant point seeks harmless. Adapt the visibility probe to your store. Omit nothing if you port dual-source cursors — dropping this guard reintroduces the silent early-exit delete bug. Coverage caveat recorded above.
