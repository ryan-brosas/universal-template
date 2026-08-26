<!-- capsule-v2 -->
# Checkpoint GC floor — after materializing versions, when is it safe to reclaim them, and which reader marks must the floor include?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How does a checkpoint reclaim version chains without breaking a reader that is pinned below (or not yet registered at) the materialization frame?

## Three-mark floor composition + per-chain materialization stamping
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs:gc_floor_reader_mark` (:1737-1757), `gc_checkpointed_table_versions` (:1759-1826), `gc_checkpointed_index_versions` (:1828-1890), `MvStore::compute_min_reader_mark` (mod.rs:9642-9654), `stamp_chain_materialized` (mod.rs:7708-7740), `gc_version_chain` rules (mod.rs:7645-7706), Finalize split (:2986-2999).
**Signature:** `fn gc_floor_reader_mark(&self) -> WalPos` = `min( min_mvcc_reader_mark, pager.min_pinned_read_frame(), mvstore.backfill_floor )`; `fn stamp_chain_materialized(&self, versions, frame: WalPos, snapshot_ts)`; `fn gc_version_chain(versions, lwm, ckpt_max, passive, min_reader_mark, drop_current_if_in_btree) -> usize`.
**Data Shape:** floor operands are all `WalPos` (seq,frame) pairs; a chain's versions carry `materialized_at: WalPos` (`ORIGIN` = never stamped); reclaim decisions consume `{lwm: u64, ckpt_max: u64, passive: bool, min_reader_mark: WalPos, drop_current_if_in_btree: bool}`.

### Decisive source
```text
// :1737-1743 — WHY the MVCC reader mark alone is insufficient:
// "The WAL read lock is held from `begin_read_tx`, so this catches it" —
//  i.e. a reader that pinned an old WAL frame but has not yet published an
//  MVCC transaction is invisible to compute_min_reader_mark; without the
//  pager-pinned term its still-needed versions get reclaimed and it then
//  reads a stale btree (the delete/index desync).
// :1753-1756 — WHY backfill bounds everything:
// "Bound by the backfill boundary: a version still materialized in
//  un-backfilled WAL frames is unreachable by a db-file reader (present or
//  future), so never reclaim it until backfilled. This is the true floor and
//  subsumes the live-reader marks."
// mod.rs:7662-7665 — the per-version gate:
// "A version's current state is reclaimable iff it is materialized in the
//  B-tree and no active reader is pinned below that materialization frame."
//   materialized_for_readers = rv.materialized_at() != ORIGIN
//                               && min_reader_mark >= rv.materialized_at()
```

**Flow:** CommitPagerTxn publishes → TruncateWal records `backfill_floor` + computes `lwm`, enters GcTableRows → per write-set row (dedup by rowid): stamp every terminal-at-snapshot version with THIS checkpoint's frame, then run the rule ladder — Rule 1 drops `(None,None)` aborted garbage; Rule 2 drops superseded tombstoned versions only once readers can reach their materialization; Rule 3 (only under blocking lock or non-passive) drops the last current copy once the B-tree owns it → GcIndexRows same over index chains → Finalize: blocking path `drop_unused_row_versions_and_slots`, passive path keeps latest SkipMap copies and unlinks empties only below `gc_floor_reader_mark()`.
**Invariant:** reclaim requires ALL of: logical invisibility (`end <= lwm`), physical durability for every possible reader (`materialized_at <= floor`), and mode-appropriate current-copy retention; empty SkipMap slots survive write-set GC on purpose (write-set retries look them up; Truncate Finalize `_and_slots` unlinks later). The begin-tx publish window (pager-pinned-but-unregistered readers) MUST be part of the floor.
**Probe:** `checkpoint_state_machine.rs::tests::gc_checkpointed_table_versions_preempts_on_large_scan` (:3642) + `gc_checkpointed_index_versions_preempts_on_large_scan` (:3715) pin chunked resume AND the slots-vs-versions split; cross-plane regression `test_issue_7638_gc_after_abandoned_checkpoint_does_not_resurrect_row` (tests/integration/mvcc.rs:1565).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "gc_floor_reader_mark gc_version_chain stamp_chain_materialized", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-operand floor (MVCC marks ∧ pager-pinned frames ∧ backfill floor) verbatim for any log+snapshot hybrid store; adapt Rule 3 gating to whether you hold exclusive access at GC time; omit the passive keep-current-copy branch if you always checkpoint stop-the-world. Coverage caveat: none material — probes are direct tests.
