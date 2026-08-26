<!-- capsule-v2 -->
# Root-page binding lifecycle — how does a table_id ↔ root_page mapping stay versioned, staged, and GC-safe across checkpoints?

**Source:** turso MIT `main@def9a0601b8e`; Codebase Memory `turso`. **Question:** MVCC table IDs are assigned at commit but pages only exist after a checkpoint — what is the full state machine of `table_id_to_rootpage`, and which transitions must never be reordered?

## Versioned bindings with a two-coordinate visibility rule: logical snapshot ts AND physical WAL reach
**Path/Symbol:** `core/mvcc/database/mod.rs`: `RootEntry` (:3908) with `covers`/`is_live` (:3928/:3935), `try_get_table_id_from_root_page_at` (:4290), `read_snapshot_ts`/`read_tx_mark` (:4313/:4323), `bump_next_table_id_below` (:4332), `record_rootpage_alloc` (:4370), `publish_rootpage_visible` (:4409), `retire_rootpage` (:4420), `gc_rootpage_entries` (:4431), `rootpage_gc_protected` (:9660), `compute_min_reader_mark` (:9642).
**Signature:** `RootEntry { root_page: Option<u64>, begin: u64, end: u64, materialized_at: WalPos }`; `is_btree_readable_at(table_id, begin_ts, read_mark)` = binding exists ∧ `root_page.is_some()` ∧ `materialized_at != STAGED` ∧ `covers(begin_ts)` ∧ `materialized_at <= read_mark`.
**Data Shape:** `WalPos` = `{checkpoint_seq, frame}` lexicographic; sentinels `ORIGIN` (always in base file) and `STAGED` (allocated, NOT yet committed). Lifecycle: `insert_table_id_to_rootpage` (live, `begin=0,end=MAX,mat=ORIGIN`) → checkpoint alloc (`root_page=Some, mat=STAGED`) → post-CommitPagerTxn publish (`mat=real WalPos`) → drop (`end=drop ts`) → GC once `end <= lwm`.

### Decisive source
```rust
// mod.rs:9626-9635 — the four-clause read gate:
//   e.root_page.is_some()
//       && e.materialized_at != WalPos::STAGED
//       && e.covers(begin_ts)
//       && e.materialized_at <= read_mark
//   // A not-yet-committed binding (materialized_at == STAGED) is never readable, even
//   // by an untracked/no-WAL reader whose mark is also STAGED.
// mod.rs:4386-4388 — one page, one live owner (freed+reused page retires the stale owner):
//   // A page has one live owner. Claiming this page means it was freed+reused; retire any
//   // stale prior owner still marked live for it (drop-time retire raced collection),
//   // else two live bindings resolve to one page (integrity_check: referenced twice).
// mod.rs:4330-4332 — id allocation must dodge recovery's canonical ids:
//   // Bump `next_table_id` below `table_id` (and below `-root_page` for a checkpointed root) so
//   // recovery's `table_id = -root_page` assignment can never collide with an existing id.
// mod.rs:4428-4430 — retired ≠ removable:
//   // Live bindings have `end == u64::MAX` and are never reclaimed — important
//   // because `compute_lwm()` is `u64::MAX` when no transactions are active.
// tests.rs:1128 region — same-epoch lower frame ⇒ unreadable; later epoch ⇒ readable via base.
```
Reverse resolution `try_get_table_id_from_root_page_at(root, snapshot_ts)`: negative roots map to themselves (canonical `id == -root_page`); positive roots scan live-or-snapshot-covering entries and take `min_by_key(end)` — end-gating makes pre-drop snapshots still resolve the old owner. Untracked txs read as `snapshot=u64::MAX` / `mark=STAGED`.

**Flow:** create → live ORIGIN binding (+ id bump below both id and -root_page) → PASSIVE alloc stamps STAGED → pages hit WAL → publish window lowers STAGED to the real position → every B-tree touch re-checks the gate (cursor side) while GC asks `rootpage_gc_protected(id, compute_min_reader_mark())` so freshly-created btrees keep version-store cover until every reader's mark reaches materialization.

**Invariant:** logical coverage alone never grants a B-tree read — physical reach (`materialized_at <= read_mark`) is a separate conjunct, and STAGED is readable by NO ONE, not even readers with maximal marks. A retired binding must survive until LWM passes its end (pre-drop snapshots resolve it), yet live bindings are exempt from that same LWM sweep precisely because an idle database's LWM is MAX.

**Probe:** `core/mvcc/database/tests.rs:1128` `mvcc_btree_read_dual_gate` drives the ENTIRE lifecycle against one reused root page 286: uncheckpointed-unreadable, STAGED-unreadable-at-max-mark, publish at `(seq=2,frame=40)` vs reader marks 39/40/epoch-3, pre-drop reverse lookup, and `gc_rootpage_entries(drop)==1` leaving the new owner. `:1189` `mvcc_try_get_table_id_stale_schema_read_returns_none` pins end-gated reverse resolution + negative-root passthrough. Coverage caveat: not executed here; verified by direct source read at def9a060.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "compute_min_reader_mark record_rootpage_alloc retire_rootpage", limit: 6, fields: ["signature", "name", "file"] });
```
(graph resolves all three in `core/mvcc/database/mod.rs`.)

## Verdict
Adopt the two-conjunct gate and the STAGED→publish→retire→GC ordering verbatim; collapsing either clock into one field reintroduces the torn-read hazard `mvcc-cursor-snapshot-gates` documents from the consumer side. Adapt WalPos to any monotonically comparable position type. Omit negative-root canonicalization if you have no SQLite schema-table heritage.
