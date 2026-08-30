<!-- capsule-v2 -->
# Optimizer cancel rollback & orphan cleanup — how does a failed or cancelled optimization restore the original segments and avoid leaking the half-built segment?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** When optimization fails mid-build or mid-swap, how are the proxy-wrapped segments restored, and why is the built-but-unswapped segment deleted only for cancellations — and what happens if the process dies instead?

## Unwrap on every error; delete the orphan only when it is provably not live
**Path/Symbol:** `lib/shard/src/optimize.rs`: `unwrap_proxy` (:98-119), `cleanup_cancelled_optimized_segment` (:132-143), error arms in `execute_optimization` (:903-917 build arm, :931-944 finish arm).
**Signature:** `pub fn unwrap_proxy(segments: &LockedSegmentHolder, proxy_ids: &[SegmentId]) -> OperationResult<()>`; `fn cleanup_cancelled_optimized_segment(segments_path: &Path, output_segment_uuid: Uuid)` (no result — best-effort).
**Data Shape:** unwrap takes the holder and the ids that were replaced by proxies; each id is swapped back to its wrapped segment under one holder write lock. Cleanup takes the output UUID (the built segment's directory name) and deletes that directory if present.

### Decisive source
```rust
// :98-119 — rollback is idempotent-tolerant:
let mut segments_lock = segments.write();
for &proxy_id in proxy_ids {
    if let Some(proxy_segment_ref) = segments_lock.get(proxy_id) {
        match locked_proxy_segment {
            LockedSegment::Original(_) => {
                // Already unwrapped. It should not actually be here
                log::warn!("Attempt to unwrap raw segment! Should not happen.");
            }
            LockedSegment::Proxy(proxy_segment) => {
                let wrapped_segment = proxy_segment.read().wrapped_segment.clone();
                segments_lock.replace(proxy_id, wrapped_segment)?;
            }
        }
    }
}
// :121-131 — orphan cleanup doc:
// "`SegmentBuilder::build` already renamed the new segment into `segments_path`, and dropping the
//  in-memory `Segment` only releases resources without deleting the directory (deletion is the
//  explicit `drop_data`). A graceful cancellation always happens before the segment is swapped
//  into the holder, so it is never live at this point and is safe to delete. Best-effort: failures
//  are logged, not propagated, so they can't mask the original cancellation error.
//  Note: this in-process cleanup is not crash safe. If the process dies between `build` and this
//  call, the orphaned segment directory is left on disk and must be reclaimed on restart instead."
// :905-916 / :932-943 — BOTH failure arms do the same two steps:
unwrap_proxy(&segment_holder, &proxy_ids)?;
// "Non-cancellation errors may occur after the swap, where the segment is live, so they are left untouched."
if matches!(err, OperationError::Cancelled { .. }) {
    cleanup_cancelled_optimized_segment(&paths.segments_path, output_segment_uuid);
}
return Err(err);
```

**Flow:** any error from the slow build OR from finish → take the holder write lock and replace every proxy id with its wrapped original segment (an Original found where a proxy was expected is warned, not fatal) → if the error is specifically `Cancelled`, best-effort delete the built segment's directory (it was renamed into place by `build` but never swapped into the holder, so it is provably not live; deletion failures only log) → propagate the original error unchanged.
**Invariant:** (1) proxies must never survive a failed optimization — readers would keep routing writes into buffers whose drain never happens; restoration is per-id and tolerant of already-restored state; (2) the orphaned built segment is deleted ONLY on cancellation — non-cancellation errors can occur after the swap, where the segment is live and deleting it destroys data; (3) in-process cleanup is explicitly NOT crash-safe: a process death between build and cleanup leaves an orphan that restart-time reclamation must find (the manifest/segment-version machinery is what makes such orphans detectable).
**Probe:** `lib/collection/src/tests/mod.rs::test_cancel_optimization` (:266-340, read whole): stop() mid-run ⇒ every logged optimizer status is `TrackerStatus::Cancelled(_)`; iterating the holder, ANY `LockedSegment::Proxy` panics ("segment is not restored"); `total_optimized_points == 0`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "unwrap_proxy cleanup_cancelled_optimized_segment cancelled optimization rollback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-step rollback (restore originals on EVERY error; delete the artifact only when the error class proves it was never published) and the explicit not-crash-safe stance with restart-time reclamation as the backstop. Adapt the error-classification to your host's cancellation type. Omit nothing else — this plane is small and fully portable.
