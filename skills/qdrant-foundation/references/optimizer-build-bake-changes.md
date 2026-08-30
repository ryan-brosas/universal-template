<!-- capsule-v2 -->
# Optimizer build & mid-build change baking — how does a merge fold in deletes, index changes, and vector-name races that happen WHILE the slow build runs?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** The optimized segment is built from frozen sources while live writes land in proxies/COW for minutes; how are those in-flight changes folded into the new segment without re-reading proxies under a long lock, and how is a deleted vector told apart from a concurrent CreateVectorName?

## Build from frozen sources, bake proxy buffers at the end
**Path/Symbol:** `lib/shard/src/optimize.rs`: `build_new_segment` (:222-414) + `optimize_segment_propagate_changes` (:429-468).
**Signature:** `fn build_new_segment<F: ?Sized + OptimizationStrategy>(factory, input_segments: &[LockedSegment], output_segment_uuid, deferred_internal_id, proxies: &[LockedSegment], permit, resource_budget, stopped, hw_counter, progress, segments_path) -> OperationResult<Segment>`; wrapper returns `(Segment, DeletedPoints)` (the `already_remove_points` diff).
**Data Shape:** inputs must all be `Original` (a Proxy input panics: "Trying to optimize a segment that is already being optimized!"); output is a built `Segment` on disk plus the set of proxy-deleted points still present in it.

### Decisive source
```rust
// :270-277 — live schema wired AFTER proxy install froze the sources:
// "Wire in the live collection schema so the merge can distinguish a deleted vector (prune it)
//  from the CreateVectorName race (cancel). Read here, after the proxy install froze the source
//  segments: the schema is persisted before a vector-name op reaches the segments, so any name a
//  frozen source carries is guaranteed visible in this read, and no concurrent create can be
//  missed (which would otherwise cause a wrong prune)."
if let Some(live_vector_names) = factory.live_vector_names() {
    segment_builder.set_live_vector_names(live_vector_names);
}
// :292-294 — index changes applied to the BUILDER with versions IGNORED:
// "Indexes are only used for defragmentation in segment builder, so versions are ignored"
for (field_name, change) in index_changes.iter_unordered() { ... }
// :350-355 — IO→CPU budget swap: "Use same number of threads for indexing as for IO.
// This ensures that IO is equally distributed between optimization jobs."
let desired_cpus = permit.num_io as usize;
let indexing_permit = resource_budget.replace_with(permit, desired_cpus, 0, stopped)...;
// :379-386 — on the BUILT segment, index changes replay in version order BEFORE deletions:
// "Apply index changes before point deletions / Point deletions bump the segment version,
//  can cause index changes to be ignored"
debug_assert!(change.version() >= old_optimized_segment_version,
    "proxied index change should have newer version than segment");
// :407-411 — buffered deletes applied to the built segment (snapshot taken just before)
for (point_id, versions) in deleted_points_snapshot {
    optimized_segment.delete_point(versions.operation_version, point_id, hw_counter).unwrap();
}
// :460-469 — precompute what the fast critical section must NOT re-delete:
// "Avoid unnecessary point removing in the critical section:
//  - save already removed points while avoiding long read locks
//  - exclude already removed points from post-optimization removing"
let already_remove_points = {
    let mut all_removed_points = proxy_deleted_points(proxies);
    for existing_point in optimized_segment.iter_points() { all_removed_points.remove(&existing_point); }
    all_removed_points
};
```

**Flow:** collect tenant defragmentation keys from input payload-index configs → wire live collection vector names into the builder (read AFTER the freeze, so the read is race-free) → copy frozen sources into the builder under per-segment read guards → apply proxy index changes to the builder unordered (defrag only) → warm vector storages (IO before CPU) → swap the IO permit for an equal-size CPU permit → build the segment to disk → snapshot proxy deletes + index changes AGAIN and apply both to the built segment (index first, version-gated, then deletes) → compute `already_remove_points` = proxy deletes minus points still present in the built segment.
**Invariant:** (1) the live-schema read must happen after the sources are frozen — schema persistence precedes vector-name ops reaching segments, so any name a frozen source carries is visible in that read; reading earlier could miss a concurrent create and wrongly prune; (2) index changes are applied twice with different semantics — unordered/versionless on the builder (defrag), ordered/version-gated on the final segment (correctness); (3) index changes must precede point deletions on the final segment because deletions bump the segment version and would make version gating drop the index changes; (4) the delete diff is computed before the critical section so the fast path never re-deletes points the build already removed.
**Probe:** no dedicated unit test drives `build_new_segment` alone (it is exercised through the full optimization tests); pinned by direct read of :222-468 plus `lib/collection/src/tests/mod.rs::test_optimization_process` (:54-160) which asserts the merged end state. Recorded caveat in verification.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "build_new_segment set_live_vector_names proxy_index_changes deleted_points_snapshot already_remove_points", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the double-application pattern (cheap unordered pass on the builder, version-gated ordered pass on the final artifact), the post-freeze live-schema read for prune-vs-race disambiguation, the IO→CPU equal-size permit swap, and the precomputed delete diff. Adapt the budget-permit machinery to your host's resource accounting. Omit tenant defragmentation keys if your host has no multi-tenant payload layout.
