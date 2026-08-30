<!-- capsule-v2 -->
# Sync points range replacement — how does a "replace this id range with this set" op stay cheap and replay-safe?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** A sync op says "the range [from_id; to_id) should now contain exactly these points". How are deletions, no-ops, and updates separated, and why does an unchanged point keep its old version?

## Five-step diff: delete absent, skip identical, upsert changed+new
**Path/Symbol:** `lib/shard/src/update/points/sync.rs`: `sync_points` (:28-37), `sync_points_raw` (:40-49), `PointToSync` trait (:52-78), `sync_points_impl` (:80-147); equality `lib/shard/src/operations/point_ops.rs`: `PointStructPersisted::is_equal_to` (:708-735), `PointStructRawPersisted::is_equal_to` (:455-480); replay-safety rationale `lib/shard/src/resolve.rs` (:44-47).
**Signature:** `pub fn sync_points(segments: &SegmentHolder, op_num: SeqNumberType, from_id: Option<PointIdType>, to_id: Option<PointIdType>, points: &[PointStructPersisted], hw_counter: &HardwareCounterCell) -> OperationResult<(usize, usize, usize)>` — returns (deleted, new, updated).
**Data Shape:** `from_id`/`to_id` bound the half-open range (None = unbounded). Stored counterparts are retrieved with payload+vector, deferred-aware (`DeferredBehavior::WithDeferred`), under a non-cancellable read (`is_stopped = AtomicBool::new(false)`).

### Decisive source
```rust
// sync.rs :80-147 — the five steps:
// 1. Retrieve existing points for a range
let stored_point_ids: AHashSet<_> = segments.iter()
    .flat_map(|(_, segment)| segment.get().read().read_range(from_id, to_id)).collect();
// 2. Remove points, which are not present in the sync operation
let points_to_remove: Vec<_> = stored_point_ids.difference(&sync_points).copied().collect();
let deleted = delete_points(segments, op_num, points_to_remove.as_slice(), hw_counter)?;
// 3. Retrieve overlapping points, detect which one of them are changed
let _num_updated = segments.read_points(existing_point_ids.as_slice(), &is_stopped,
    DeferredBehavior::WithDeferred, |ids, segment| {
        let stored_records = P::retrieve_stored(&**segment, ids, ...)?;
        for (id, stored_record) in stored_records {
            if !point.is_equal_to(&stored_record) { points_to_update.push(*point); updated += 1; }
        }
        Ok(updated)
    })?;
// 4. Select new points  (sync set minus stored set)
// 5. Upsert points which differ from the stored ones
let num_replaced = upsert_points_impl(segments, op_num, points_to_update, hw_counter)?;
debug_assert!(num_replaced <= num_updated, ...);

// point_ops.rs :708-735 — is_equal_to: id + per-name vector equality + payload
// where empty and non-existent payloads are considered equal
if self_vectors.len() != segment_vectors.len() { return false; }
for (name, vec) in segment_vectors {
    if self_vectors.get(name) != Some(VectorRef::from(vec)) { return false; }
}
self_payload == segment_payload   // after .filter(|p| !p.is_empty()) on both sides
```

**Flow:** read the whole range across all segments → delete stored ids missing from the incoming set → for overlapping ids, retrieve stored records and compare → identical points are skipped entirely (no write, no version bump) → changed plus brand-new points go through the normal two-phase upsert. The raw variant compares storage-native bytes, so it never decodes vectors.
**Invariant:** (1) an unchanged point keeps its OLD segment version — the test pins `point_version(2) == before` while the changed point gets `op_num`; skipping is what makes repeated full-range syncs cheap; (2) replay-safety without submit-time resolution: every point a sync touches is alive and version-guarded, so re-applying the same record against later state is a no-op or a correct overwrite (this is exactly why `is_filter_resolving` returns false for SyncPoints, resolve.rs :44-47); (3) empty payload equals absent payload in the equality check; (4) the returned triple counts deleted / new / updated, with replaced ≤ updated asserted.
**Probe:** `lib/shard/src/update/tests.rs::test_sync_points_raw` (:155-219, read WHOLE at pin): segment holds points 1-5; sync set = {unchanged point 2, byte-changed point 3, new point 100} ⇒ (deleted==3 [1,4,5 gone], new==1, updated==1); point 2's version unchanged, point 3's version == 100 with byte-exact vector round-trip.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "sync_points range replace delete missing upsert changed points", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the diff-before-write shape: range read → set difference deletes → per-point equality gate → upsert only the delta, returning a (deleted, new, updated) triple. Adapt the equality predicate to your record type (qdrant splits decoded vs raw-bytes via a trait with an associated StoredRecord type). Omit the non-cancellable read flag if your read path has no cancellation concept. Caveat: the equality gate must compare the FULL record (all named vectors + payload), not just presence — a partial compare silently turns updates into no-ops.
