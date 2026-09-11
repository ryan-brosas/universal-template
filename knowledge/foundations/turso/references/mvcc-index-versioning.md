<!-- capsule-v2 -->
# MVCC index versioning — how do secondary-index entries participate in optimistic concurrency without a row to point at?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** How are unique-index conflicts checked and index versions tracked when the "row" is just a key blob?

## Sortable-key chains + prefix-range conflict scan with SQLite NULL semantics
**Path/Symbol:** `core/mvcc/database/mod.rs:1805` (`check_index_for_conflicts`), rules :1893-1933 region ("deliberately skip non-unique indexes and NULL keys — SQLite semantics"), insert path `insert_index_version` (:4995-5012, canonical Arc keys), `SortableIndexKey` type, shadow-check twin `index_chain_invalidates_btree` (cursor.rs:477) and `query_btree_version_is_valid`.
**Signature:** unique-index validation runs a PREFIX-KEY range scan over the index SkipMap rather than a point lookup, because the stored key may differ in trailing columns while colliding on uniqueness columns.
**Data Shape:** index rows live in per-table (`MVTableId`) SkipMaps keyed by `Arc<SortableIndexKey>`; each value is the same `RowVersions<A>` chain type tables use — full reuse of visibility/conflict machinery.

### Decisive source
```rust
// mod.rs:5000-5004 — identity dedup feeding savepoint tracking:
// returns the canonical Arc (ours on miss, an existing one on hit), which we
// hand to savepoint tracking.
// mod.rs:1893-1933 region — scan discipline:
// unique indexes only; NULL keys never conflict (SQLite: UNIQUE allows
// multiple NULLs); non-unique indexes carry no conflict authority.
```
Because index keys sort as encoded bytes (`SortableIndexKey`), the prefix range [uniqueness-columns] catches every variant regardless of payload tail. Deletes/updates mirror the table path (eager conflict on visible entry, :5209-5216). The B-tree side asks the inverse question via `IndexShadowFinger::btree_row_is_valid` → `!db.index_chain_invalidates_btree(versions, tx_id)` — one predicate family, two directions.

**Flow:** write index entry → chain under canonical sortable key | commit → for each touched unique index: prefix range scan → any committed end_ts > begin_ts ⇒ WriteWriteConflict.
**Invariant:** NULL and non-unique exclusions are SEMANTIC (SQLite compat), not optimizations — dropping them changes observable behavior; key identity must be canonical-Arc so ledgers match map slots.
**Probe:** tests.rs:14887/:14943 staged-conflict probes cover the index lane; hermitage P4/G-single pin observable outcomes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "check_index_for_conflicts SortableIndexKey insert_index_version", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt chain-reuse over a separate index-concurrency design. Adapt sort encoding to your key format. Omit prefix-scan machinery if you have no unique constraints.
