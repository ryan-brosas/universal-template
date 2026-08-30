<!-- capsule-v2 -->
# MVCC checkpoint publish window — how do you materialize versions while concurrent transactions keep running?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How does a checkpoint write B-tree pages without stop-the-world, and what exactly happens inside the brief serialized moment?

## Passive collection + staged root-map + single publish window
**Path/Symbol:** `core/mvcc/database/checkpoint_state_machine.rs:step_inner` (:1952-3010), PrepareCheckpoint passive gate (:1955-1983), CommitPagerTxn (:2713-2798), `try_begin_passive_publish_window` (mod.rs:7033-7038), RootMapOp (:137-144), AcquireLock snapshot sampling (:1990-2020).
**Signature:** Passive mode: collection AND the btree-write phase run WITHOUT the blocking lock — "The only serialized point is the brief publish window in CommitPagerTxn." Blocking mode: takes the RW lock up front (Busy on contention). Passive entry uses a CAS gate (`checkpoint_in_progress`) instead of the lock, because "which would turn a contended explicit TRUNCATE into a silent no-op" is unacceptable for the flag-off path.
**Data Shape:** root-map mutations are STAGED during collection as `RootMapOp::{Alloc, Retire, Remove}` and applied only in the publish window; new bindings stay physically invisible to readers (`visible_from = u64::MAX`) until post-commit.

### Decisive source
```text
// checkpoint_state_machine.rs:1955-1962:
// "The passive checkpoint acquires the blocking lock only after collection, so
//  it needs an explicit single-orchestrator gate. The blocking (flag-off) path
//  takes the lock up front and gets that invariant — plus Busy-on-contention —
//  from the lock itself, so it must NOT use this gate…"
// :2216-2221 — visibility staging:
//   "the pages are not durable until CommitPagerTxn, so it stays physically
//    invisible to readers (visible_from = u64::MAX) until the post-commit
//    publish window. Undo-logged: reverted if the checkpoint fails before
//    commit."
```

Snapshot discipline: blocking samples `snapshot_ts` AFTER acquiring the lock ("no concurrent commits can land between snapshot_ts and collection"); passive samples then re-validates bounds at publish ("already-durable index deletes are not replayed"). On commit failure the `?` rolls back the pager txn; durable_txid_max and the log offset stay put, so a retry re-stages from the previous boundary. A contended passive publish window yields a completion for retry (auto path) or returns Busy (explicit).

**Flow:** snapshot → collect versions/schema view unlocked → stage root ops → begin+write+commit pager txn atomically with metadata row → CAS the brief publish window → apply root-map ops + backfill floor → continue world.
**Invariant:** nothing globally visible may change before the publish window; everything the write phase staged must be undo-logged until that window commits.
**Probe:** `test_passive_checkpoint_tolerates_concurrent_create_after_snapshot` (tests.rs:4858); `mvcc_passive_auto_checkpoint_retries_publish_while_reader_pinned` (:1007); `mvcc_passive_checkpoint_busy_under_pinned_reader_no_corruption` (:964).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "passive publish window checkpoint_in_progress RootMapOp", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt collect-unlocked/publish-briefly for any online materialization; adapt the CAS gate vs lock choice to your contention model; omit schema-view reconstruction if your schema cannot drift mid-checkpoint. Coverage caveat: none material — probes are direct tests.
