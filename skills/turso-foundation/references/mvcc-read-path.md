<!-- capsule-v2 -->
# MVCC read-path plumbing — how does a row read resolve across the version store, and what must NOT happen when nothing is visible?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What does the read path return for a row that exists only as invisible garbage, and how do index reads differ?

## Reverse-scan first-visible; None is data; index reads reuse table machinery via RowKey
**Path/Symbol:** `core/mvcc/database/mod.rs:5330-5345+` (`read` / `read_from_table_or_index`), reverse iteration discipline (shared with conflict scans), `RowKey::{Record, ...}` enum distinguishing table rowids from index records (:5222-5224 panic guard "Index deletes must have a record row_id").
**Signature:** `pub fn read_from_table_or_index(&self, tx_id, id: &RowID, maybe_index_id: Option<MVTableId>) -> Result<Option<Row>>`.
**Data Shape:** `RowID{table_id, row_id: RowKey}` — one id type covers both planes; `Ok(None)` = no VISIBLE version (row may physically exist as aborted garbage or below-reader history).

### Decisive source
```rust
// :5245-5251 region — visibility precedes everything on delete; reads mirror it:
// A transaction cannot delete a version that it cannot see, nor can it conflict with it.
// if !rv.is_visible_to(tx, &self.txs, &self.finalized_tx_states) { continue; }
```
The read loop walks the chain in REVERSE (newest first) so the first visible version is the correct snapshot view — matching conflict-scan order for cache friendliness. Because rollback leaves `(None,None)` ghost versions in place (lazy SkipMap removal), readers MUST treat invisibility as normal: `None` flows up as "no such row" without any physical cleanup. Index reads route through the same predicates keyed by `SortableIndexKey` instead of rowid.

**Flow:** tx lookup (NoSuchTransactionID otherwise) → chain fetch → reverse scan → first `is_visible_to` hit → clone row | exhausted ⇒ Ok(None).
**Invariant:** never conflate "not visible" with "absent" — GC owns reclamation; visibility checks always consult BOTH maps before any conservative default.
**Probe:** hermitage G1a/OTV assert invisible-history reads; `test_hermitage_aborted_transaction_not_visible` pins Ok(None) semantics end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "read_from_table_or_index RowID NoSuchTransactionID", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reverse-first-visible scanning with tri-state absence. Adapt error taxonomy to your result type. Nothing here is omittable — it's the smallest complete read contract.
