<!-- capsule-v2 -->
# Deferred-points exclusion & optimizer dedup — when a point's newest copy is invisible (deferred), how do filtered updates avoid acting on a stale visible copy, and who eventually removes it?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** With `prevent_unoptimized`-style deferred points, a point can have an old non-deferred copy that matches a filter while its newest deferred copy does not; how does a filtered update decide NOT to touch that point, and what component later removes the stale copy?

## Exclude at update time, dedup at optimization time — one seam, two halves
**Path/Symbol:** `lib/shard/src/update/helpers.rs`: `deferred_points_to_exclude_by_filter` (:23-58, doc :13-22) + `points_by_filter` (:75-116); consumer `lib/shard/src/update/points/delete.rs`: `delete_points_by_filter` (:52-99); optimizer half: `lib/shard/src/optimize.rs`: `finish_optimization` deferred-dedup block (:588-607) → `lib/shard/src/segment_holder/mod.rs`: `deduplicate_points` (:894-901).
**Signature:** `pub(super) fn deferred_points_to_exclude_by_filter(segments: &SegmentHolder, per_segment_points: &AHashMap<SegmentId, Vec<PointIdType>>) -> AHashSet<PointIdType>`; `pub fn deduplicate_points(&self, points: &[PointIdType], hw_counter) -> OperationResult<()>`.
**Data Shape:** input is the per-segment filter-match map (read with `DeferredBehavior::WithDeferred`); output is the set of point ids the operation must skip entirely. The dedup half takes point ids and deletes every version of them except the highest-versioned one, across all segments.

### Decisive source
```rust
// helpers.rs :13-22 (doc):
// "When a point has multiple copies across segments, the old non-deferred copy may match
//  a filter while the newest deferred copy does not. In this case, the operation should NOT
//  be applied to the point — the old copy will be cleaned up during optimization deduplication."
// :30-40 — max matched version per point across segments:
let version = segment.point_version(*point_id);
*entry = std::cmp::max(*entry, version);
// :46-56 — exclude when the NEWEST copy is deferred and newer than anything that matched:
if segment.has_point(*point_id, DeferredBehavior::WithDeferred)
    && segment.point_version(*point_id) > *max_version
    && segment.point_is_deferred(*point_id)
{ to_exclude.insert(*point_id); }
// :104-110 — wired into every filtered update read, only when some segment has deferred points:
if has_deferred {
    let to_exclude = deferred_points_to_exclude_by_filter(segments, &per_segment_points);
    if !to_exclude.is_empty() { affected_points.retain(|id| !to_exclude.contains(id)); }
}
// delete.rs :80-84 — same corner case in by-filter delete, phrased as KEEP set:
// "If the latest version of a point is deferred and does not match the filter, we need to skip
//  deletion for all copies and let deduplication during optimization delete old points."
let points_to_keep = deferred_points_to_exclude_by_filter(segments, &points_to_delete);
// optimize.rs :598-606 — the optimizer half, post-swap under a read lock:
// "Deferred points in proxy segment may become visible for optimized segment (in most cases).
//  It's time to deduplicate them and remove older versions from optimized segment, where they
//  were visible while deferred status."
deferred_points.chunks(CHUNK_SIZE /* 100 */)
    .try_for_each(|chunk| read_segment_holder.deduplicate_points(chunk, hw_counter))?;
// segment_holder/mod.rs :891-900 — "It scans all segments for presence of the points, detects
// points with the highest version, and removes all other versions of the points from all segments."
let (_to_keep, to_delete) = self.find_points_to_update_and_delete(points);
self.delete_points_from_segments(to_delete, hw_counter)
```

**Flow:** filtered read collects per-segment matches including deferred points → if any segment holds deferred points, compute per-point max matched version, then exclude every point whose newest copy is deferred AND strictly newer than the max match → the operation applies only to the survivors (delete-by-filter expands survivors to ALL their copies so no stale twin survives the op) → later, when an optimization swaps out the proxies, the holder deduplicates exactly those deferred point ids: highest version kept, all other versions deleted from all segments.
**Invariant:** (1) an operation must never act on a point whose newest version is invisible — applying it to the stale visible copy would resurrect behavior the newest (deferred) version already superseded; the stale copy is left for dedup, never deleted ad hoc; (2) exclusion requires ALL THREE conditions — point present with deferred, its version strictly greater than the max matched version, and it being deferred — so a matching deferred head or an equal-version state still applies normally; (3) the two halves are coupled: if updates stop excluding, dedup alone cannot fix already-applied ops; if the optimizer stops deduping, excluded stale copies accumulate forever.
**Probe:** `lib/collection/src/tests/deferred_points_dedup.rs::test_deferred_points_dedup_after_optimization` (:225-309, read whole): prevent_unoptimized shard with indexing_threshold=1; two CoW overwrite rounds each asserting deferred points exist before waiting out optimization; final `assert_no_duplicate_point_ids` (:142-223) asserts at most one non-deferred AND at most one deferred copy per point across all segments.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "deferred_points_to_exclude_by_filter points_by_filter deduplicate_points deferred", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-condition exclusion test and the split responsibility (updates refuse to touch points whose newest copy is invisible; the optimizer is the single component that removes stale versions). Adapt the per-segment match map to your storage layout. Omit the whole seam only if your host has no deferred/unindexed point state — with it, both halves are required together.
