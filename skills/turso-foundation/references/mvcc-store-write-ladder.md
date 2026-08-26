<!-- capsule-v2 -->
# MVCC store write ladder — which four insert variants and one delete rule does every table/index mutation funnel through?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** The MvStore exposes `insert`/`update`/`upsert`/`delete`, but the cursor calls a wider `_to_table_or_index` family — what distinct version shapes must a porter reproduce, and where exactly can conflicts surface?

## Four constructors × two planes; delete is eager-visible-only with an unreachable conflict arm
**Path/Symbol:** `core/mvcc/database/mod.rs`: `insert_to_table_or_index` (:4969), `insert_tombstone_to_table_or_index` (:5039), `insert_btree_resident_to_table_or_index` (:5088), `update_to_table_or_index` (:5173), `upsert_to_table_or_index` (:5194), `delete_from_table_or_index` (:5225-5313), `is_write_write_conflict` (:9785).
**Signature:** all take `(tx_id: TxID, …, maybe_index_id: Option<MVTableId>)`; table plane = single shared `self.rows` SkipMap keyed by full `RowID{table_id, row_id}`; index plane = one SkipMap per index (`index_rows[index_id]`) keyed by `Arc<SortableIndexKey>` — the canonical Arc is returned by `insert_index_version` so savepoint/write-set tracking keys stay pointer-identical to map keys.
**Data Shape:** each variant differs ONLY in its `RowVersion` header fields:

| variant | begin | end | btree_resident |
|---|---|---|---|
| insert | `TxID(tx)` | `None` | false |
| tombstone | **`None`** | `TxID(tx)` | true |
| btree_resident | `TxID(tx)` | `None` | true |
| delete (in place) | unchanged | set to `TxID(tx)` on the visible version | unchanged |

### Decisive source
```rust
// mod.rs:5010-5014 — inserts are purely optimistic; conflicts NEVER happen here:
//   // NOTE: We do NOT check for conflicts at insert time (pure optimistic).
//   // Conflicts are detected at commit time using end_ts comparison.
//   // This allows multiple transactions to insert the same rowid,
//   // with first-committer-wins semantics.
// mod.rs:5048-5050 — why the tombstone has no creator begin:
//   // Tombstones over B-tree-resident rows have no MVCC creator begin.
//   // They invalidate B-tree visibility via end timestamp only.
// mod.rs:5249-5257 — delete scans newest→oldest, skips invisible versions, and
//   // A transaction cannot delete a version that it cannot see,
//   // nor can it conflict with it.
//   if !rv.is_visible_to(…) { continue; }
//   if is_write_write_conflict(…) {
//       turso_assert_reachable!("write-write conflict on delete");
//       return Err(LimboError::WriteWriteConflict);
// mod.rs:5173-5182 — update = conditional delete-then-insert (false if nothing deleted);
// upsert = unconditional delete-then-insert (bails on Err only).
```
Every arm ends with `tx.insert_to_write_set(id/row_versions)` + `record_created/deleted_*_version(version_id)` — rollback (`rollback_row_version` :9674) and commit-time validation consume these ledgers, not the chains directly.

**Flow:** resolve tx from `txs` (assert Active) → pick plane → build the variant's RowVersion via `get_version_id()` → `insert_version`/`insert_index_version` (GC-retry loop re-checks `table_versions_still_mapped` via `Arc::ptr_eq`, :7786-7801) → bump rowid allocator (table inserts only) → record ledger entries in the transaction.

**Invariant:** (1) conflicts are impossible at insert time and unreachable-but-typed at delete time — the eager `WriteWriteConflict` return sits behind `turso_assert_reachable!`, which per `macros/src/lib.rs:69` is a NO-OP that never panics ("Pending better SQL generation"), so the delete conflict arm is provably dead under HEAD's visibility-first scan; real first-committer-wins fires at COMMIT via `check_version_conflicts` (Hekaton p.301 rule quoted at :9779-9783). (2) A delete may only stamp `end=TxID(tx)` on a version the deleting tx can SEE; invisible versions are skipped silently. (3) Tombstone ≠ delete: it CREATES a chain for a row the MV store has never seen because the B-tree owns the live data.

**Probe:** `core/mvcc/database/tests.rs:14823` `test_speculative_delete_hides_committed_version` — T3's eager update stamps `end=TxID(T3)`, yet T2's later `insert_btree_resident_to_table_or_index` still commits-conflicts against T1: a speculative delete must not hide the underlying version from commit checks. `:14887` `test_committed_delete_tombstone_conflict` — a committed pure-delete tombstone (`begin=None, end=TxID(Td)`) is caught by commit validation. Both are API-level tests over this exact ladder.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "insert_to_table_or_index delete_from_table_or_index", limit: 6, fields: ["signature", "name", "file"] });
```
(graph resolves both to `core/mvcc/database/mod.rs` :4969-5035 / :5225-5313.)

## Verdict
Adopt the four-shape table and the optimistic-insert/eager-invisible-only-delete split verbatim — porting eager conflict detection into the delete scan (or adding a begin ts to tombstones) breaks the Hekaton contract the commit path validates against. Adapt allocator/plumbing calls to your transaction object. Omit the index-plane canonical-Arc dance if your maps own their keys.
