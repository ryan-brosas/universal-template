<!-- capsule-v2 -->
# Segment error latch — what happens after one point write fails mid-operation?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** How does a segment quarantine a failed write so newer operations fail fast, yet let the failed operation itself be retried?

## SegmentFailedState latch and clear-on-retry
**Path/Symbol:** `lib/segment/src/segment/segment_ops.rs`: `handle_point_version_and_failure` (:558-612).
**Signature:** `fn handle_point_version_and_failure<F>(&mut self, op_num: SeqNumberType, point_id: PointIdType, op_point_offset: Option<PointOffsetType>, operation: F) -> OperationResult<bool>`.
**Data Shape:** latch = `Option<SegmentFailedState { version: SeqNumberType, point_id: Option<PointIdType>, error: String }>` on the segment; every routed point write passes through this wrapper.

### Decisive source
```rust
if let Some(SegmentFailedState { version: failed_version, .. , error }) = &self.error_status {
    // Failed operations should not be skipped,
    // fail if newer operation is attempted before proper recovery
    if *failed_version < op_num {
        return Err(OperationError::service_error(
            format!("Not recovered from previous error: {error}")));
    } // else: Re-try operation
}

let res = self.handle_point_version(op_num, op_point_offset, operation);

match get_service_error(&res) {
    None => match &self.error_status {
        Some(error) if error.point_id == Some(point_id) => {
            log::info!("Recovered from error: {}", error.error);
            self.error_status = None;              // Fixed
        }
        _ => {}
    },
    Some(error) => {
        self.error_status = Some(SegmentFailedState {
            version: op_num, point_id: Some(point_id), error });
    }
}
res
```

**Flow:** operation fails → segment records `(version=op_num, point_id, error)` → any NEWER op (`failed_version < op_num`) is rejected with "Not recovered from previous error" — this blocks the WAL apply loop at that entry instead of silently diverging → ops with equal-or-older versions pass through (retry path) → when the failing point+version retries successfully, the service-error check finds `None`, matches `error.point_id == Some(point_id)`, logs "Recovered from error", clears the latch.
**Invariant:** (1) the latch is per-segment but cleared only by success on the SAME point id — an unrelated successful write does not clear it; (2) ordering matters: the stale-op rejection must fire BEFORE running the new op; (3) without the latch, a partially applied multi-step write followed by later independent writes would leave the segment in a mixed state that crash recovery cannot reason about.
**Probe:** direct test coverage caveat: no dedicated unit test asserts the latch transitions in `lib/segment/src/segment/tests/mod.rs`; the invariant is pinned by reading the decisive range :558-612 directly at pin plus its two callers (`handle_point_mutate` :438-490, `handle_point_version_and_failure` call sites). Recorded as a test-gap caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "SegmentFailedState error status not recovered from previous error handle point version failure", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fail-fast latch with same-point retry clearing. Adapt the error payload type to your error taxonomy. Omit the legacy "ToDo: Recover previous segment state" behavior — qdrant itself does not roll back partial state; it relies on WAL replay.
