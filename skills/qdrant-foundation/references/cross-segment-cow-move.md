<!-- capsule-v2 -->
# Cross-segment CoW move — how does a point escape a non-appendable segment without losing durability?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** When an upsert targets a point living in a proxy or non-appendable segment, how is it moved to a writable segment such that a crash can never lose it?

## Flush dependency + raw-byte move + conditional delete
**Path/Symbol:** `lib/shard/src/segment_holder/mod.rs`: `apply_points_with_conditional_move` (:987-1130), `aloha_random_write` (:925-961).
**Signature:** `fn apply_points_with_conditional_move<'op, F, G>(&self, op_num: SeqNumberType, ids: &[PointIdType], point_operation: F, point_cow_operation: G, hw_counter: &HardwareCounterCell) -> OperationResult<AHashSet<PointIdType>>`.
**Data Shape:** `can_apply_operation = !write_segment.is_proxy() && write_segment.is_appendable()`; otherwise the CoW path: `retrieve_raw` returns `(raw_vectors: SmallVec<[(VectorNameBuf, Vec<u8>); 1]>, payload)`; destination receives one fused `upsert_moved_point`.

### Decisive source
```rust
// Durability ordering: destination persisted BEFORE source delete
self.flush_dependency.lock().add_dependency(idx, appendable_idx, op_num);

// Deferred-aware read: a plain VisibleOnly read would report the point missing
// while a `prevent_unoptimized` optimization races this upsert.
let mut record = write_segment.retrieve_raw(
    &[point_id], &WithPayload { enable: true, payload_selector: None },
    &WithVector::Bool(true), hw_counter, &stopped, DeferredBehavior::WithDeferred,
)?.remove(&point_id).ok_or(OperationError::PointIdError { missed_point_id: point_id })?;

// Names overlaid with fresh data don't travel as bytes.
raw_vectors.retain(|(name, _)| updated_vectors.get(name).is_none());

// One fused write instead of per-step clones on append-only destinations
appendable_write_segment.upsert_moved_point(op_num, point_id, &raw_vectors, updated_vectors, &payload, hw_counter)?;

// Keep the source of the CoW operation as the deferred point is invisible until indexing.
if !appendable_write_segment.point_is_deferred(point_id) {
    write_segment.delete_point(op_num, point_id, hw_counter)?;
}
```

**Flow:** source is proxy/non-appendable → pick a destination via `aloha_random_write` (try each candidate's `try_write()` first for a lock-free win; if all contended, block on ONE randomly chosen candidate; empty candidate list = service error) → register flush dependency src→dst at op_num → read the source head as storage-native bytes including deferred heads → apply the caller's CoW closure to overlay changed vectors/payload → fused upsert into the destination → delete the source ONLY if the new copy is not itself deferred. A `debug_assert` requires vector configs on both sides to be encoding-compatible (size/distance/datatype/multivector) while segment-role fields (storage type, index, quantization) may legitimately differ.
**Invariant:** (1) the flush dependency makes "destination bytes durable before source tombstone durable" a flush-ordering property — dropping it can lose the point on crash between the two writes; (2) vectors move as raw stored bytes, never dequantize→requantize; (3) reads must include deferred points or a racing deferred optimization surfaces as spurious "No point with id found"; (4) deleting the source when the destination copy is deferred would make the point invisible until indexing completes.
**Probe:** direct tests, both read directly at pin: `lib/shard/src/update/tests.rs::test_upsert_points_raw_moves_point_from_non_appendable` (:99-152 — non-appendable flag set by hand, asserts source no longer has the point, destination has byte-exact vectors, payload preserved for the moved point and absent for the fresh insert, `updated == 1`) and `lib/shard/src/segment_holder/tests.rs::test_cow_operation` (:215-301 — CoW closure replaces vector `[0,1,2,3]`→`[9;4]` and payload 42→2 in an appendable segment).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "apply points conditional move aloha random write flush dependency retrieve raw deferred", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the write-before-delete flush dependency, deferred-aware raw retrieval, byte-exact CoW transfer, and the deferred-copy retention rule. Adapt `aloha_random_write`'s contention policy and the flush-dependency registry to your locking/flush machinery. Omit the concrete `SegmentEntry` trait surface and TurboQuant datatype details.
