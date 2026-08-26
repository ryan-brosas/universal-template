<!-- capsule-v2 -->
# Point version gating ladder — when is a stale update ignored, and why does equality still apply?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** At which three layers is an update dropped as stale, and why must `version == op_num` still be *applied* at the segment layer while being skipped at the holder layer?

## Holder `>=` skip → segment `>` ignore
**Path/Symbol:** `lib/shard/src/segment_holder/mod.rs`: `apply_points_with_conditional_move` gate (~:1004-1010); `lib/segment/src/segment/segment_ops.rs`: `handle_point_version` (:640-670), `handle_point_mutate` same-op rule (:438-490).
**Signature:** `fn handle_point_version<F>(&mut self, op_num: SeqNumberType, op_point_offset: Option<PointOffsetType>, operation: F) -> OperationResult<bool>`.
**Data Shape:** versions are WAL sequence numbers (`SeqNumberType`); per-point slot version lives in the id tracker; segment-level `version` bumps on any successful write.

### Decisive source
```rust
// holder level — skip if this op already touched the point:
if let Some(point_version) = write_segment.point_version(point_id)
    && point_version >= op_num
{ applied_points.insert(point_id); return Ok(false); }

// segment level :644-652 — ignore only STRICTLY older ops:
if let Some(point_offset) = op_point_offset
    && self.id_tracker.borrow().internal_version(point_offset)
        .is_some_and(|current_version| current_version > op_num)
{ return Ok(false); }

let (applied, internal_id) = operation(self)?;
self.bump_segment_version(op_num);
if let Some(internal_id) = internal_id {
    self.id_tracker.borrow_mut().set_internal_version(internal_id, op_num)?;
}
```

**Flow:** an upsert is a multi-step point write (insert/replace vectors, then payload). The holder's `>=` check prevents re-entering a segment that already applied *this exact op*, while the segment's strict `>` allows the SAME op's later steps (e.g. `set_full_payload` right after `upsert_point`) to proceed. `handle_point_mutate` completes the picture: if the slot version already equals `op_num`, mutate in place — it cannot be durable yet (the segment write lock spans the whole operation; versions flush last and crash recovery replays the WAL), so no reader can have observed it.
**Invariant:** (1) mixing the comparisons breaks either idempotency (holder must be `>=`) or multi-step writes (segment must be strictly `>`); (2) version bookkeeping (`bump_segment_version`, `set_internal_version`) happens only AFTER the operation succeeds — a failed step leaves versions untouched for retry; (3) unknown points always apply regardless of op number.
**Probe:** direct test `lib/segment/src/segment/tests/mod.rs::test_handle_point_version` (:1795-1844), read directly at pin: with point 1 stored at version 100, op 99 → `assert!(!applied)`; op 100 → `applied`; op 101 → `applied`; `op_point_offset: None` applies at every version.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "handle point version internal version bump segment version set internal version", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-comparison ladder plus success-only version advancement. Adapt the storage of per-point versions to your id tracker. Omit the Rust closure-based mutation plumbing; port the comparison semantics exactly.
