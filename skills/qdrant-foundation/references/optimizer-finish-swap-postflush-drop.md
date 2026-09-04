<!-- capsule-v2 -->
# Optimizer finish: swap & post-flush drop — in what order does the fast critical section replay proxy buffers, swap segments, and retire source files without losing WAL-replay pre-images?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** After the slow build, how are buffered vector-name/index/delete changes applied to the optimized segment, how is it swapped in for the proxies, and why must the old segments' files survive until a flush even though their proxies are already evicted?

## Ordered replay → swap → dedup → manifest → deferred drop, under one upgradable lock
**Path/Symbol:** `lib/shard/src/optimize.rs`: `finish_optimization` (:480-646). Drop target: `lib/shard/src/segment_holder/mod.rs`: `register_segment_drop` (:479-501) over `register_post_flush_action` (:462-473).
**Signature:** `fn finish_optimization(segment_holder: &LockedSegmentHolder, locked_proxies: Vec<LockedSegment>, mut optimized_segment: Segment, already_remove_points: &DeletedPoints, proxy_ids: &[SegmentId], cow_segment_id_opt: Option<SegmentId>, stopped, hw_counter) -> OperationResult<usize>` (returns point count).
**Data Shape:** consumes the built segment plus the three proxy buffer kinds; returns the optimized segment's available point count; side effects: holder swap, COW removal, deferred-point dedup, manifest sync, one post-flush drop action per evicted proxy.

### Decisive source
```rust
// :490-495 — "This block locks all write operations with collection. It should be fast."
let upgradable_segment_holder = segment_holder.upgradable_read();
let update_guard = segment_holder.acquire_updates_lock();
// :497-498 — phase order 1: "Apply vector name changes before index and point changes /
// New named vectors must exist before indexes or points reference them"
// :515-522 — supersedes_wrapped ⇒ delete_vector_name FIRST:
// "The optimised segment was built from the wrapped data, so it currently carries the *old*
//  schema for this name. `create_vector_name_impl` is idempotent and would silently keep that
//  old storage; clear it first so the new schema actually takes effect."
// :531-537 — phase order 2 (index): "Apply index changes before point deletions / Point deletions
// bump the segment version, can cause index changes to be ignored"; note a change version may be
// LOWER than the segment version because it was already applied during the build.
// :557-566 — phase order 3 (deletes), DIFFED against what the build already removed:
let points_diff = deleted_points.iter()
    .filter(|&(point_id, _)| !already_remove_points.contains_key(point_id));
// :571-584 — upgrade to write, swap, then remove the temp COW if it survived:
let (_, proxies) = writable_segment_holder.swap_new(optimized_segment, proxy_ids);
debug_assert_eq!(proxies.len(), proxy_ids.len(), "swapped different number of proxies");
// "Temp segment might be taken into another parallel optimization so it is not necessary exist"
writable_segment_holder.remove_segment_if_not_needed(cow_segment_id)?;
// :586-607 — DOWNGRADE to read for deferred dedup in CHUNK_SIZE=100 batches:
// "Deferred points in proxy segment may become visible for optimized segment (in most cases).
//  It's time to deduplicate them and remove older versions from optimized segment..."
deferred_points.chunks(CHUNK_SIZE)
    .try_for_each(|chunk| read_segment_holder.deduplicate_points(chunk, hw_counter))?;
// :609-612 — "It is important to update manifest before we retire proxy data, as we don't want
// to have a situation, where new segment is not yet registered, but old segment data is already
// dropped."
read_segment_holder.sync_segment_manifest(None)?;
// :614-636 — files must survive until a flush proves the optimization durable:
// "WAL replay can only re-derive those moves from the on-disk pre-images, so the files must
//  survive until a flush proves this optimization durable." The ack pin the proxy imposed while
// alive ("its persistent_version reported the wrapped source's durable point while its version
// climbed with every propagated change") is gone after swap_new evicted it, so:
for proxy in proxies {
    let ack_pin = proxy.get().read().persistent_version();
    read_segment_holder.register_segment_drop(optimized_segment_version, ack_pin, proxy);
}
```

**Flow:** upgradable-read + updates mutex → replay vector-name intents in version order (superseded names deleted before create) → replay index changes in version order (tolerating already-applied lower versions) → apply buffered deletes minus the build-time diff → upgrade to write: `swap_new(optimized, proxy_ids)`, remove the temp COW if still present → downgrade to read: dedup deferred points from the swapped-out proxies in 100-id chunks → sync the segment manifest → register one post-flush drop per evicted proxy with `ready_at = optimized_segment_version` and `ack_pin = proxy.persistent_version()` → release holder lock, then updates mutex, then proxy Arcs.
**Invariant:** (1) replay order is mandatory — vector names before indexes/points (references must resolve), index changes before deletes (deletes bump the segment version and would gate out later index changes); (2) the critical section stays fast — everything expensive happened in the build; only ordered replay + swap + dedup run under the lock; (3) the manifest is synced BEFORE any source file can be dropped — a persisted manifest referencing a deleted segment loses data on replica load; (4) source files are destroyed only by a post-flush action gated on the durable waterline covering the optimized segment's version, with the WAL ack pinned at each source's final persistent version until then — deleting them earlier would break WAL replay of CoW moves whose pre-images lived in those files; (5) the temp COW may legitimately be gone (stolen by a parallel optimization) — removal is conditional, not an error.
**Probe:** `lib/collection/src/tests/mod.rs::optimization_keeps_manifest_consistent_with_live_segments` (:161-232) pins invariant 3 as a regression test: after draining optimizations, the persisted manifest equals the live segment set exactly and never references an optimized-away UUID; `test_optimization_process` (:54-160) pins the swap end state (inputs gone, total_optimized_points==119).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "finish_optimization swap_new register_segment_drop sync_segment_manifest deduplicate_points", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ordered-replay-then-swap structure, the conditional COW removal, the manifest-before-retire ordering, and the membership-independent ack pin re-expressed as a post-flush drop action. Adapt the upgradable-read/upgrade/downgrade ladder to your lock library. Omit the deferred-point dedup chunking if your host has no deferred (unindexed) point state.
