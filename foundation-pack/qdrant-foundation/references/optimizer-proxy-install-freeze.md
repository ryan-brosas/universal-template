<!-- capsule-v2 -->
# Optimizer proxy install & freeze — how does an optimizer freeze its input segments for a merge without losing concurrent writes or ghosting points out of search?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** When an optimization (merge/index/vacuum) starts, how are the input segments wrapped so writes keep landing, the deleted-mask race window is closed, and the new COW segment is registered before any write can reach it?

## Two-phase install: build proxies unlocked, freeze under one write lock
**Path/Symbol:** `lib/shard/src/optimize.rs`: `execute_optimization` (:747-952). Callers (trace_path inbound): `lib/shard/src/optimizers/segment_optimizer.rs`: `SegmentOptimizer::optimize` (1 hop), `lib/collection/src/update_workers/optimization_worker.rs`: `UpdateWorkers::launch_optimization` (2 hops).
**Signature:** `pub fn execute_optimization<F: ?Sized + OptimizationStrategy>(optimizer_name, segment_holder, input_segment_ids, output_segment_uuid, deferred_internal_id, paths, permit, resource_budget, stopped, progress, telemetry_counter, factory, on_successful_start) -> OperationResult<OptimizationResult>`.
**Data Shape:** inputs are segment ids; output is `OptimizationResult { points_count }`. A temp COW segment plus a `NewSegmentToken` (obligation to register it in the manifest) may be created; proxies replace inputs in the holder; `running_optimizations` counter increments and is held until the swap.

### Decisive source
```rust
// :769-774 — COW decision: writes must keep landing somewhere
let has_appendable_segments_except_optimized = appendable_segments_ids
    .iter().any(|id| !input_segment_ids.contains(id));
let need_extra_cow_segment = !has_appendable_segments_except_optimized;
// :783-790 — missing or already-proxied inputs are a NO-OP, not an error
let all_segments_ok = input_segments.len() == input_segment_ids.len()
    && input_segments.iter().all(|s| matches!(s, LockedSegment::Original(_)));
if !all_segments_ok { return Ok(OptimizationResult { points_count: 0 }); }
// :809-818 — phase 1 under upgradable-read only:
let proxy = UnsyncedProxySegment::new(sg.clone());
// Wrapped segment is fresh, so it has no operations / Operation with number 0 will be applied
if let Some(extra_cow_segment) = &extra_cow_segment_opt {
    proxy.replicate_field_indexes(0, &hw_counter, extra_cow_segment)?;
}
// :820-828 — BEFORE the freeze: register COW in manifest, then save its version
// "Register the freshly added cow segment in the manifest before we save the version,
//  it guarantees that no writes will happen into unregistered segment."
segment_holder_read.sync_segment_manifest(extra_cow_token_opt)?;
SegmentVersion::save(segment_path)?;
// :836-886 — phase 2 under ONE write-lock upgrade:
debug_assert_matches!(proxy.wrapped_segment(), LockedSegment::Original(_),
    "during optimization, wrapped segment must not be another proxy segment"); // PR #7208
// :854-861 — "An upsert/delete could have raced onto the still-appendable wrapped segment
// between UnsyncedProxySegment::new and this lock; syncing here makes the mask cover the
// segment's full final point range — otherwise a point inserted in that window sits past
// the mask and scored search treats it as deleted. The type-state guarantees this happens
// exactly once and cannot be skipped."
let proxy = proxy.finalize();
// :863-869 — replicate_field_indexes a SECOND time under the full lock
// ("optimized segments could have been changed ... we can afford this operation under
//  the full collection write lock")
segment_holder_write.replace(idx, locked_proxy.clone())?;
// :878-883 — add_new_locked(cow); running_optimizations.inc() right after the replace
```

**Flow:** upgradable-read → decide whether an extra COW segment is needed (only when ALL appendable segments are optimization inputs) → validate inputs (race-lost optimization returns a zero-point no-op) → disk-fit preflight → create temp COW + token → wrap each input in an `UnsyncedProxySegment` and replicate field indexes to the COW at version 0 → manifest-sync the COW and save its version file → upgrade to the holder write lock ONCE → per input: assert wrapped is not a proxy, `finalize()` the proxy (deleted-mask snapshot from the now-frozen segment), re-replicate indexes, `replace(idx, proxy)` → add the COW → bump the running-optimizations counter → release the lock and start the slow build.
**Invariant:** (1) the deleted-mask snapshot MUST be taken under the write lock that freezes the wrapped segment — a point racing in between construction and freeze sits past a stale mask and scored search treats it as deleted (type-state makes finalize exactly-once); (2) the new COW segment is registered in the manifest and version-saved BEFORE it can receive writes — an unregistered-but-written segment is lost on restart; (3) wrapping a proxy with another proxy is forbidden (assert) because proxies share state through their write segment, which would break delete-propagation soundness (PR #7208); (4) index replication happens twice — once cheaply before the freeze, once authoritatively under the full lock.
**Probe:** `lib/collection/src/tests/mod.rs::test_cancel_optimization` (:266-340) pins the install/rollback pair: after a mid-run stop, every segment is `LockedSegment::Original` again (a leftover proxy panics the test) and `total_optimized_points == 0`; `test_optimization_process` (:54-160) pins the happy path end state (inputs gone, 4 segments left, 119 points optimized).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "execute_optimization UnsyncedProxySegment finalize replicate_field_indexes need_extra_cow_segment", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-phase install (construct unlocked, freeze+finalize under one exclusive lock), the exactly-once type-state finalize, the manifest-before-writes registration order, and the race-lost-inputs-as-no-op policy. Adapt the parking_lot upgradable-read/upgrade idiom to your lock library. Omit the second index replication if your host has no concurrent index changes during optimization.
