<!-- capsule-v2 -->
# Chunked two-phase upsert — where do new points land, and why is the write chunked?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** How does a batch upsert split between updating existing points in place and inserting brand-new points, without starving concurrent readers?

## UPDATE_OP_CHUNK_SIZE + smallest-appendable insert
**Path/Symbol:** `lib/shard/src/update/points/upsert.rs`: `UPDATE_OP_CHUNK_SIZE` (:20-23), `upsert_points_impl` (:162-217); `lib/shard/src/segment_holder/mod.rs`: `bump_max_segment_version_overwrite` (:611-614).
**Signature:** `pub(super) fn upsert_points_impl<'a, P>(segments: &SegmentHolder, op_num: SeqNumberType, points: impl IntoIterator<Item = &'a P>, hw_counter: &HardwareCounterCell) -> OperationResult<usize> where P: PointToUpsert`.
**Data Shape:** input deduped into `AHashMap<PointIdType, &P>` (last duplicate wins by map insertion of keys); returns count of applied points; error `OperationError::service_error("No appendable segments exist, expected at least one")` when no writable segment exists.

### Decisive source
```rust
// :20-23
/// Do not insert more than this number of points in a single update operation chunk
/// This is needed to avoid locking segments for too long, so that
/// parallel read operations are not starved.
const UPDATE_OP_CHUNK_SIZE: usize = 32;

// :163-165 — dedup first: one id, one upsert
let points_map: AHashMap<PointIdType, &P> = points.into_iter().map(|p| (p.id(), p)).collect();
// :172-178 phase A: update existing points via conditional move
let updated_points = segments.apply_points_with_conditional_move(
    op_num, ids_chunk,
    |id, write_segment| points_map[&id].upsert_into(write_segment, op_num, hw_counter),
    |id, raw_vectors, updated_vectors, old_payload| { /* CoW move */ ... },
    hw_counter)?;
// :196-199 phase B: never-found ids go to the SMALLEST appendable segment
let default_write_segment =
    segments.smallest_appendable_segment().ok_or_else(|| {
        OperationError::service_error("No appendable segments exist, expected at least one")
    })?;
```

**Flow:** per 32-id chunk → phase A tries every segment for each id (`apply_points_with_conditional_move`, version-gated) → ids not updated and not found are inserted in a single locked pass into the *smallest* appendable segment (spreads growth toward the segment closest to optimizer thresholds) → `unlock_fair` releases the write guard promptly → next chunk. Empty upsert batches (`process_point_operation` empty `UpsertPoints`/`UpsertPointsRaw` arms) skip all segments but still call `bump_max_segment_version_overwrite(op_num)` (an `AtomicU64::fetch_max`) so the WAL can acknowledge an operation that touches nothing.
**Invariant:** (1) chunk bound 32 caps segment lock-hold time; porting with unbounded chunks starves readers; (2) inserts require at least one appendable segment — during optimizer swap windows this is a hard service error, not a queue; (3) an empty batch must still bump the persisted-version waterline or its WAL entry can never be acknowledged.
**Probe:** direct tests: `lib/shard/src/update/tests.rs::test_upsert_points_raw_moves_point_from_non_appendable` (:99-152, asserts `updated == 1` when one of two ids already existed in a non-appendable segment and both end up byte-exact in the appendable target) and the `assert_eq!(updated, ...)` contracts read directly at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "upsert points impl chunk smallest appendable segment apply points conditional move", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt two-phase chunked upsert, smallest-appendable insert policy, and the empty-batch version-waterline bump. Adapt chunk size to your locking model and the appendable-segment selection to your compaction policy. Omit the concrete `PointInsertOperationsInternal` conversion plumbing.
