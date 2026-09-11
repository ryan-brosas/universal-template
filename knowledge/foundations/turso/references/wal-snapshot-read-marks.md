<!-- capsule-v2 -->
# WAL snapshot isolation — how do read-mark slots coordinate readers, the writer, and the checkpointer without conversations?

**Source:** turso (MIT) @ main`def9a060`; Codebase Memory `turso`. **Question:** How do I encode snapshot bounds as lock-protected values so maintenance and queries coordinate through data?

## Read-mark slots (ports SQLite's aReadMark)
**Path/Symbol:** `core/storage/wal.rs` WalSnapshot + slots 1-4 (:997-1055), SQLite commentary port (:2800-2860), packed u64 lock word (:230-330), contention ladder (:3355-3395), BusySnapshot upgrade (:3405-3430), savepoint restore asserts (:4520-4555).
**Signature:** Readers take `WalSnapshot {max_frame, nbackfills, last_checksum, checkpoint_seq, transaction_count}`. If everything is backfilled (`max_frame == nbackfills`) they take **slot 0** and ignore the WAL entirely — the steady-state fast path that also lets RESTART proceed once readers drain. Otherwise they claim one of slots 1-4, exclusive-CASing its value to max_frame, then RE-validate after locking.
**Data Shape:** the lock word packs writer bit | 31 reader bits | 32-bit value into one u64 — "updated atomically together while sitting in a single cpu cache line" (:230-330).

### Decisive source
```text
// wal.rs:2800-2860 — SQLite commentary ported verbatim:
//   readers holding READ_LOCK(0) "always ignore the entire WAL";
//   "the checkpointer may only transfer frames where the frame numbers are
//    ≤ every aReadMark[] in use."
// :3405-3430 — the upgrade error is distinct on purpose:
//   a stale snapshot during read→write upgrade returns BusySnapshot, not
//   Busy — "Retrying with busy_timeout will NEVER HELP".
```

Contention behavior mirrors SQLite exactly (:3355-3395): yields for retries 6-9, quadratic backoff `(cnt-9)² × 39µs` after that, hard failure at 100. Savepoint rollback restores `(frame, checksum, checkpoint_seq)` captured in RollbackTo and ASSERTS generation match — turso needs none of SQLite's cross-checkpoint clamping because positions are only ever captured under the held write lock (:4520-4555). MVCC consumes these marks too: `min_pinned_read_frame` feeds version-store GC floors (see mvcc-gc-two-clocks).

**Flow:** reader CAS-claims slot at max_frame → re-validates under lock → reads; checkpointer transfers only frames ≤ every held mark; full-backfill ⇒ slot 0 fast path.
**Invariant:** never lower an occupied reader's mark; encode bounds as values protected by their own locks, not by protocol promises. Verified HEAD-current anchors: lock word packs writer bit | 31 reader bits | 32-bit value into one u64 ("updated atomically together while sitting in a single cpu cache line", :264); READ_LOCK(0) commentary at :2761; BusySnapshot return at :3407 ("Retrying with busy_timeout will NEVER HELP", :3398-3400); MVCC GC bridge = `min_pinned_read_frame` (:566/:776/:876).
**Probe:** wal.rs ~10145-10205 asserts slot-0 behavior after full backfill (`find_frame → None` since all content is in the DB file); ~9330-9365 forces Retry by occupying all four slots and asserts no leaked guard or slot.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "turso", query: "WalSnapshot read mark slot busy_snapshot", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt read-mark value coordination + slot-0 fast path verbatim; adapt slot count to your concurrency target; omit quadratic backoff tuning until contention is measured. Coverage caveat: none material.
