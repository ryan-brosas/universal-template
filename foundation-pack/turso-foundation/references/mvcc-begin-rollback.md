<!-- capsule-v2 -->
# MVCC begin/rollback — why must snapshot publication be atomic with its timestamp, and why is rollback in-place invalidation?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How do I publish a snapshot without racing GC, and roll back without surgically editing version chains?

## Begin: one clock-lock critical section; Rollback: mark + in-place rewrite
**Path/Symbol:** `core/mvcc/database/mod.rs` begin (:6055-6135), rollback (:6520-6590), live-map removal (:6140-6180), savepoints (:6830-6900), in-place Hekaton §2.4 rewrite (:9640-9660).
**Signature:** Begin allocates begin_ts AND inserts the Transaction into the live map inside the SAME clock-lock critical section. Rollback marks Aborted → cascades abort_now → rewrites each write-set version in place → removes from live map only after every chain lock was acquired (ASSERTing an empty dependency set — "those dependencies will wait forever (deadlock)").
**Data Shape:** created versions become `(None, None)` bounds (invisible garbage the normal GC sweep reclaims); deleted rows simply lose their end timestamp, undoing the deletion.

### Decisive source
```text
// mod.rs:6055-6135 — the begin-publish window:
// "This closes the 'begin-publish window': between allocating a snapshot
//  timestamp and inserting into txs, the txn is invisible to compute_lwm.
//  Inline GC runs on the commit path… so a writer that commits in that window
//  could compute an LWM above our begin_ts and reclaim a version this snapshot
//  still needs - a snapshot-isolation violation."
```

Savepoint rollback is finer-grained: savepoints track created/deleted version ids, retain created versions by id, clear `end` on deleted ones, and prune write-set entries only when no surviving uncommitted version remains (:6830-6900).

**Flow:** begin = {alloc ts; insert} atomic → rollback = mark aborted → cascade dependents → in-place invalidate versions → unlock-checked live-map removal.
**Invariant:** never split timestamp allocation from live-map insertion; never remove a live transaction with non-empty dependency set; never surgically delete chains on rollback.
**Probe:** `core/mvcc/database/tests.rs:10441` — rollback leaves versions with `(None, None)` bounds and `drop_unused_row_versions()` returns 1 while the SkipMap slot remains (lazy removal).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "compute_lwm rollback begin_ts live map", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt atomic begin-publication (the GC race is real and silent) and in-place rollback reclamation; adapt savepoint bookkeeping to your write-set representation; omit savepoint pruning rules until you have partial rollback. Coverage caveat: none material.
