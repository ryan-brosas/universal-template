<!-- capsule-v2 -->
# MVCC cursor snapshot gates — which two read-time checks keep a long-lived cursor honest against checkpoint materialization?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** A cursor opened before a PASSIVE checkpoint publishes can outlive the world it compiled against — what must every B-tree touch re-verify, and why is one gate logical+physical while the other resolves to reprepare?

## Dual gate (logical base-validity AND physical page visibility) + stale-schema fallibility
**Path/Symbol:** `core/mvcc/cursor.rs`: `MvccLazyCursor::is_btree_allocated` (:792-803), constructor root-page resolution (:556-572); store side `is_btree_readable_at` / `read_snapshot_ts` / `read_tx_mark` (`core/mvcc/database/mod.rs`), `try_get_table_id_from_root_page_at` (:568).
**Signature:** `fn is_btree_allocated(&self) -> bool` = `db.is_btree_readable_at(&table_id, begin_ts, read_mark)`; ctor: `db.try_get_table_id_from_root_page_at(root, snapshot_ts).ok_or(LimboError::SchemaUpdated)?`.
**Data Shape:** inputs = reader's `begin_ts = read_snapshot_ts(tx_id)` and `read_mark = read_tx_mark(tx_id)`; predicate = binding covers this snapshot AND pages were already durable when the read mark was pinned (`visible_from <= observed_boundary`).

### Decisive source
```rust
// cursor.rs:793-798 — the dual-gate contract:
//   // Dual gate (logical base-validity AND physical visibility): a PASSIVE checkpoint may
//   // materialize this object's btree during collection. This cursor may read it only if
//   // the binding covers our snapshot AND its pages were already durable when we pinned
//   // our read mark (`visible_from <= observed_boundary`). A cursor that opened before
//   // checkpoint publish materialization therefore stays version-store-only for its whole
//   // life and never seeks the page its read mark can't see.
// cursor.rs:561-569 — stale schema is a reprepare, not an invariant violation:
//   // Under PASSIVE checkpointing a transaction can capture a schema cookie older than
//   // the drop committed within its own snapshot … The compiled cursor then points at a
//   // positive root page its snapshot already sees dropped. That is a stale-schema read,
//   // not an invariant violation: reprepare against the current schema instead of panicking.
```
The gate runs on EVERY btree advance/seek/exists entry point (:853, :940, :1077, :1979), so mid-scan publication flips the cursor's remaining work to the MVCC-only path rather than faulting on unreadable pages.

**Flow:** open → resolve table_id from root page at snapshot ts (fallible ⇒ SchemaUpdated reprepare under passive checkpointing; infallible assert otherwise) → per operation re-ask `is_btree_allocated` → false ⇒ treat btree_peek as Exhausted and run version-store-only.

**Invariant:** a cursor never reads a B-tree page outside its pinned read mark; "b-tree not readable for my snapshot" is indistinguishable from "no B-tree rows yet" to all iteration logic.

**Probe:** `core/mvcc/database/tests.rs:2408` (`test_btree_resident_recovery_then_checkpoint_delete_stays_deleted`) pins the btree-resident lifecycle across recovery/checkpoint; :17255 region documents republished-root statements failing with `SchemaUpdated`. Coverage caveat: tests not executed here; both gates verified by direct source read at def9a060.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "is_btree_readable_at try_get_table_id_from_root_page_at retired_rootpages read_tx_mark", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the rule that cursor-vs-DDL staleness surfaces as a typed reprepare error while cursor-vs-checkpoint staleness degrades to version-store-only reads — never conflate the two. Adapt thresholds to your checkpoint machinery. Omit the negative-root-page canonicalization if you lack SQLite-style schema tables. Coverage caveat recorded above.
