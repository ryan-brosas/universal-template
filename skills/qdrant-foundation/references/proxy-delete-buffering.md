<!-- capsule-v2 -->
# Proxy mutation strike + delete buffering — how does a segment that must not accept writes still serve deletes during optimization?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** While an optimizer rebuilds a segment behind a ProxySegment, which write operations are rejected, which are buffered, and what state does the buffered delete mutate?

## All point mutations error; only deletes buffer into shared map + local mask
**Path/Symbol:** `lib/shard/src/proxy_segment/segment_entry.rs`: disabled ops (:817-925), live `delete_point` (:929-1007); struct fields `lib/shard/src/proxy_segment/mod.rs`:28-46.
**Signature:** `fn delete_point(&mut self, op_num: SeqNumberType, point_id: PointIdType, _hw_counter: &HardwareCounterCell) -> OperationResult<bool>`.
**Data Shape:** `deleted_points: AHashMap<PointIdType, ProxyDeletedPoint>` where `ProxyDeletedPoint { local_version, operation_version }`; `deleted_mask: Option<BitVec>` keyed by point OFFSET (wrapped-local); `deleted_deferred_count: usize`.

### Decisive source
```rust
// :817-827 — every data mutation is a hard service error:
fn upsert_point(&mut self, op_num: SeqNumberType, point_id: PointIdType,
                _vectors: NamedVectors, ...) -> OperationResult<bool> {
    Err(OperationError::service_error(format!(
        "Upsert is disabled for proxy segments: operation {op_num} on point {point_id}")))
}
// :929-1007 — but delete_point buffers instead of erroring:
self.version = cmp::max(self.version, op_num);   // version advances with NO data change
match &self.wrapped_segment {
    LockedSegment::Original(raw) => { /* record only if get_internal_id(point_id).is_some() */ }
    LockedSegment::Proxy(proxy)  => { /* record only if has_point(point_id, WithDeferred) */ }
}
if was_deleted && was_deferred_point { self.deleted_deferred_count += 1; }
```

**Flow:** update op targets a proxied segment → upsert/payload/vector mutations fail fast with service errors (the holder routes real writes elsewhere) → `delete_point` checks whether the WRAPPED segment actually holds the id (deferred-aware on the Proxy branch), records `{op_num, op_num}` into the shared `deleted_points` map only then, marks the point's offset in the proxy's own `deleted_mask`, bumps `self.version`, and counts deferred victims so callers can wait for them.
**Invariant:** (1) a proxy never mutates wrapped point data — deletes are intent records, not tombstone writes; (2) `self.version` still advances on buffered deletes so later same-proxy ops are version-gated correctly; (3) an id absent from the wrapped segment is NOT recorded (it may live in another segment of the holder); (4) re-deleting the same id asserts (debug) monotonically newer `operation_version`.
**Probe:** direct test `lib/shard/src/proxy_segment/tests.rs::test_read_filter` (:330-399, read at pin): after wrapping a 2-point segment and `delete_point(100, 2)`, both filtered and unfiltered `read_filtered` shrink by exactly 1 — the buffered delete is visible through reads before any propagation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "proxy segment delete point buffered deleted points deferred count disabled upsert", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the split contract: reject data mutations, buffer deletes as (id → operation_version) intents plus a local offset mask, advance the wrapper version without touching wrapped bytes. Adapt the shared-map ownership (qdrant shares `deleted_points` across sibling proxies via a common write segment). Omit the double-proxy (`LockedSegment::Proxy`) branch if your host forbids nesting proxies.
