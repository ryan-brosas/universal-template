<!-- capsule-v2 -->
# MVCC cursor delete/insert write-path — how do you delete or upsert a row that may exist only in a version store, only in a B-tree, or in both?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** When a cursor's current row can be MVCC-resident or B-tree-resident, what distinguishes insert vs update vs tombstone — and why must the record be pre-fetched before any IO?

## Write routing on the Loaded{in_btree} position
**Path/Symbol:** `core/mvcc/cursor.rs`: `MvccLazyCursor::insert` (:1749-1844), `MvccLazyCursor::delete` (:1846-1913), helpers `read_from_table_or_index` / `insert_to_table_or_index` / `insert_btree_resident_to_table_or_index` / `insert_tombstone_to_table_or_index` (`core/mvcc/database/mod.rs`).
**Signature:** `fn insert(&mut self, key: &BTreeKey) -> Result<IOResult<()>>`; `fn delete(&mut self) -> Result<IOResult<()>>`.
**Data Shape:** routing inputs are the CURRENT position (`CursorPosition::Loaded { row_id, in_btree, .. }`) plus existence probes; outputs are exactly one of update-into-MVCC / btree_resident-marker / fresh-insert / tombstone. `was_btree_resident = *in_btree && *current_row_id == row.id` is computed BEFORE overwriting `current_pos` (:1798-1811).

### Decisive source
```rust
// cursor.rs:1827-1831 — the third write class no naive port has:
// } else if was_btree_resident {
//     // The row exists in B-tree but not in MvStore - mark it as B-tree resident
//     // so that checkpoint knows to write deletes to the B-tree file.
//     self.db.insert_btree_resident_to_table_or_index(self.tx_id, row, maybe_index_id)
// :1876-1884 — delete's tombstone rule + rolled-back-row escape:
// If was_deleted is false, this can ONLY happen when we have a row that only exists
// in the btree but not the mv store. In this case, we create a tombstone for the row
// based on the btree row.  … The cursor can also be positioned on a row that was
// rolled back after seek. That row does not exist in either MVCC or the B-tree.
```
Four-way INSERT routing (:1817-1841): visible version ⇒ `update_to_table_or_index`; else if `was_btree_resident` ⇒ `insert_btree_resident_to_table_or_index` (checkpoint later writes the DELETE into the B-tree); else ⇒ plain `insert_to_table_or_index`. Every failure arm resets `current_pos = BeforeFirst` via `inspect_err` — position is never left claiming a half-written row.

**Flow:** delete: assert `in_btree ⇒ is_btree_allocated()` → pre-fetch `record()` if in_btree → `delete_from_table_or_index` → on false + in_btree build the tombstone from the NOW-synchronous record → `invalidate_record`. Insert: resolve RowID from TableRowId/IndexKey → compute `was_btree_resident` → route (above) → reposition `current_pos` onto the written row preserving `in_btree: was_btree_resident`.

**Invariant:** (1) an UPDATE of a B-tree-only row must go through the btree_resident variant, not a plain insert — otherwise checkpoint never materializes the deletion and the old B-tree row resurrects after restart; (2) `delete()` is NOT IO-reentrant w.r.t. `delete_from_table_or_index` side effects, so the record fetch MUST happen before it (:1864-1869 comment: "the VDBE may never have materialized the row's record (e.g. UPDATE through a DeferredSeek never calls Column on the table cursor). Pre-fetch it here so the later synchronous fetch used to build a tombstone doesn't have to yield IO"); (3) a rolled-back seek target silently no-ops instead of erroring.

**Probe:** `core/mvcc/database/tests.rs:2408` (`test_btree_resident_recovery_then_checkpoint_delete_stays_deleted`), :4783 (`test_rollback_of_indexed_update_keeps_btree_resident_index_entry`), :4819 (`test_conflict_abort_of_indexed_update_keeps_btree_resident_index_entry`), :4951 (`test_checkpoint_retry_does_not_replay_checkpointed_btree_resident_unique_delete`) — all four pin the btree_resident lifecycle end-to-end. No cargo runner in the inspo clone; probes verified by direct source read at def9a060.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "insert_tombstone_to_table_or_index insert_btree_resident_to_table_or_index delete_from_table_or_index MvccLazyCursor insert delete", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-way write routing keyed on (visible-version?, was-btree-resident?) and the pre-fetch-before-non-reentrant-write rule. Adapt storage calls to your version store/checkpoint pair. Omit SQLite-specific DeferredSeek plumbing if your executor has no deferred index→table seek. Coverage caveat: none of these four tests execute in this environment; they are cited as upstream behavioral pins read directly at HEAD.
