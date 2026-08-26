<!-- capsule-v2 -->
# MVCC WAL position tracking — how do version rows remember where their bytes live on disk, and what resets that memory?

**Source:** turso MIT `main@def9a060`; Codebase Memory `turso`. **Question:** What bookkeeping lets a row version know "I am readable from the B-tree at WAL position X" so GC and checkpoint agree?

## materialized_at: WalPos with ORIGIN sentinel; any mutation resets to ORIGIN
**Path/Symbol:** `core/mvcc/database/mod.rs:473` (`materialized_at: WalPos` field), :1027-1035 (field doc: reachable only if `materialized_at <= read_mark`), constructor default `WalPos::ORIGIN` (:9851-9856), reset rule (:9720-9722: "over-resetting is safe: it only delays GC, never reclaims early"), consumer `is_btree_readable_at` (:9620-9660).
**Signature:** `pub(crate) fn set_materialized_at(&mut self, pos: WalPos)` — called when checkpoint materializes the version's current state into a durable B-tree page.
**Data Shape:** one u64-ish position per version (not per chain); ORIGIN = never materialized. The physical-GC floor is min over readers' frozen read-marks (`min_pinned_read_frame` from WAL read-mark slots).

### Decisive source
```rust
// mod.rs:1027-1029 — field contract:
// reachable by this transaction only if `materialized_at <= read_mark`
// — i.e. ...
// :9620-9660 region — why the gate exists:
// without is_btree_readable_at, "a transaction that opened before a
// checkpoint materialization would seek a page its read mark cannot reach
// (a torn/foreign/zeroed-page read)."
```
The reset-on-mutation rule closes the stale-position hazard: if a version's content changes after materialization (set_begin/set_end during speculation resolution or rewrite), its old B-tree copy no longer reflects it, so ORIGIN restores the conservative default. Over-resetting merely delays GC — an explicitly chosen failure direction.

**Flow:** version created {ORIGIN} → checkpoint writes it into pager/WAL → set_materialized_at(pos) → GC may reclaim once pos ≤ every reader's read-mark AND LWM passed | any later mutation ⇒ back to ORIGIN.
**Invariant:** a version is B-tree-readable iff materialized_at within all reader floors AND content unchanged since stamping; when in doubt, reset toward ORIGIN (delay), never forward.
**Probe:** tests.rs:10485-region chain GC asserts no version below backfill floor drops; #7638 tombstone trap is the named failure of getting this wrong.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "materialized_at WalPos is_btree_readable_at", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-version durable-position stamps for any store bridging an in-memory layer and a paged file. Adapt WalPos to your log addressing. The reset-toward-conservative rule transfers to ANY stamped-validity design.
