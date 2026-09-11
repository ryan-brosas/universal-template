<!-- capsule-v2 -->
# Pre-WAL filter resolution — how do filter-carrying update ops keep WAL replay deterministic?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** A delete-by-filter or conditional upsert selects its targets by reading live segment state; if that op is replayed later against different state, it hits a different point set. Where and how is the filter frozen into a concrete id list?

## Classification + rewrite before the append, fenced by a queue drain
**Path/Symbol:** `lib/shard/src/resolve.rs`: module contract (:1-17), `is_filter_resolving` (:35-74), `resolve_operation` (:84-168), `matched_ids` (:172-182), `resolve_conditional_upsert` (:202-216); fence `lib/collection/src/shards/local_shard/resolve_submit.rs`: module docs (:1-26), `LocalShard::submit_update_filter_resolving` (:71-128).
**Signature:** `pub fn resolve_operation(segments: &SegmentHolder, operation: CollectionUpdateOperations, hw_counter: &HardwareCounterCell) -> OperationResult<CollectionUpdateOperations>`; `pub fn is_filter_resolving(operation: &CollectionUpdateOperations) -> bool`.
**Data Shape:** input is any collection update op; output is the SAME enum with only pre-existing id-based variants (WAL format unaffected). `matched_ids` returns sorted, deduped ids. The rewritten record reuses the incoming operation's single clock tag — one tag covers exactly one WAL record.

### Decisive source
```rust
// resolve.rs :1-10 — why this exists:
//! Filter-carrying operations decide which points they touch by reading live
//! segment state. Persisting them as-is makes WAL replay nondeterministic:
//! replay-time state can differ from the original apply-time state, so a
//! replayed filter can select a different point set (see issue #9575).
//! These helpers rewrite such operations into their id-based equivalents
//! *before* they are written to the WAL...

// resolve.rs :35-74 — SyncPoints is deliberately NOT filter-resolving:
//   // `SyncPoints` reads current state too, but every point it touches
//   // is alive and version-guarded, so its replay is protected by the
//   // per-point version checks.
| PointOperations::SyncPoints(_) | PointOperations::SyncPointsRaw(_) => false,

// resolve_submit.rs :71-128 — the fence, in order:
let _fence = self.update_lock.write().await;          // 1. block new submits
self.update_sender.load().send(UpdateSignal::Plunger(plunger_sender)).await?;
plunger_receiver.await ...;                            // 2. drain: all appended ops applied
let resolved = tokio::task::spawn_blocking(move || {
    let segments = segments.read();
    resolve_operation(&segments, operation, ...)      // 3. rewrite against drained state
}).await??;
debug_assert!(!shard::resolve::is_filter_resolving(&resolved), ...); // drift guard
self.append_and_dispatch(OperationWithClockTag::new(resolved, clock_tag), wait, ...).await
// 4. append+dispatch still inside the fence; WAL lock NOT held across the drain
//    (the worker takes it for re-reads/flushes — holding it here deadlocks)
```

**Flow:** submit classifies via `is_filter_resolving` → non-resolving ops take the plain path → resolving ops take the fence: write-lock the update lock (in-flight submits already appended+enqueued), push a Plunger through the update queue so every previously-appended op is applied first, resolve the filter against the now-exact segment state (sorted+deduped ids because per-segment matches flatten with duplicates), assert the result no longer classifies as resolving, then append+dispatch the single rewritten record under the same fence.
**Invariant:** (1) the WAL only ever contains id-based forms of these ops from this version on; (2) resolution sees exactly the ops preceding the rewrite in WAL order — nothing may be appended between resolve and append; (3) the rewrite emits ONE record reusing the incoming clock tag (untagged/tag-sharing records break WAL-delta recovery); (4) the apply path still supports filter ops, so old-version WALs containing raw filter records replay with by-filter semantics.
**Probe:** `lib/collection/src/tests/wal_recovery_test.rs::test_filter_ops_resolved_to_ids_in_wal` (:1176-1357, read at pin): after a conditional insert-only upsert and a clock-tagged delete-by-filter, every WAL record satisfies `!is_filter_resolving`, the conditional reduced to a plain upsert of only the new point, and the rewritten delete carries the exact incoming clock tag. Companion `test_old_wal_filter_op_replays_with_apply_semantics` (:1358-1492): a raw-appended old-style DeletePointsByFilter replays through the kept by-filter apply path (points 2,3 gone, 1,4,5 remain).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "resolve_operation rewrite filter resolving operation id-based before WAL", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-part contract: a pure classifier (`is_filter_resolving`) plus a pure rewriter (`resolve_operation`) over the same op enum, executed under a fence that drains the apply queue between "read state" and "append". Adapt the fence to your host's update channel (any mechanism that proves all prior ops applied). Omit the clock-tag single-record constraint if you have no tagged WAL-delta recovery. Caveat: classifier and rewriter must be kept in lockstep — qdrant pins this with a debug_assert, not a type.
