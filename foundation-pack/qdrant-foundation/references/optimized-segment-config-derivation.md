<!-- capsule-v2 -->
# Optimized-segment config derivation — how do you decide what the post-compaction segment should look like, based on how big it will be?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** When an optimizer merges N segments into one, what determines whether the result gets an HNSW index + quantization or stays plain, in-RAM or mmap storage — and why must deferred points force an index even below the size threshold?

## Threshold-driven output config, shared by every optimizer
**Path/Symbol:** `lib/shard/src/optimizers/segment_optimizer.rs`: `SegmentOptimizer::optimized_segment_builder` (:163-377, default trait method — merge/indexing/vacuum/config-mismatch all inherit it), `max_num_indexing_threads` (:33-45). Policy plane: `SegmentOptimizer` trait (:80-119) fixes name/paths/config/thresholds/`plan_optimizations`/`optimize`; `ShardOptimizationStrategy` (:49-70) adapts a concrete optimizer to the execution kernel's `OptimizationStrategy` (create_segment_builder / create_temp_segment / live_vector_names) consumed by pass-5's `execute_optimization`.
**Signature:** `fn optimized_segment_builder(&self, optimizing_segments: &[LockedSegment]) -> OperationResult<SegmentBuilder>`.
**Data Shape:** input = the ORIGINAL segments to be merged (a `LockedSegment::Proxy` input returns service error "Proxy segment is not expected here" :186-192); per-vector-name byte totals are summed across inputs; output is a `SegmentBuilder` over a derived `SegmentConfig` (dense + sparse vector data, payload storage type).

### Decisive source
```rust
// :207-221 — the two thresholds are judged on the LARGEST per-name vector store
let maximal_vector_store_size_bytes = bytes_count_by_vector_name.values().max().copied().unwrap_or(0);
let threshold_is_indexed = maximal_vector_store_size_bytes >= thresholds.indexing_threshold_kb.saturating_mul(BYTES_IN_KB);
let threshold_is_on_disk = maximal_vector_store_size_bytes >= thresholds.memmap_threshold_kb.saturating_mul(BYTES_IN_KB);
// :226-227 — deferred points force HNSW even below the indexing threshold
// We must always create an HNSW index if we have deferred points to be able to promote them
if threshold_is_indexed || any_has_deferred {
    // assign Indexes::Hnsw(hnsw_config) + quantization_config per dense vector name
}
// :263 — dense storage ladder (excerpt): requested Cold wins with Mmap
Some(Memory::Cold) => config.storage_type = VectorStorageType::Mmap,
// :313-324 — sparse index type: big ⇒ Mmap (Cold|Cached) / ImmutableRam (Pinned), small ⇒ MutableRam
let is_big = threshold_is_on_disk || threshold_is_indexed;
let index_type = if is_big {
    match requested_memory {
        Memory::Cold | Memory::Cached => SparseIndexType::Mmap,
        Memory::Pinned => SparseIndexType::ImmutableRam,
    }
} else { SparseIndexType::MutableRam };
// :327-335 — persist ONLY the explicit `memory` param so legacy configs stay
// byte-identical for older versions ("which older Qdrant versions can load without any unknown fields")
config.index.memory = segment_optimizer_config.sparse_vector.get(vector_name).and_then(|cfg| cfg.memory);
```

**Flow:** sum per-vector-name bytes over all inputs (Proxy ⇒ error) → take the max name as the sizing basis → compute `threshold_is_indexed` (≥ indexing_threshold_kb) and `threshold_is_on_disk` (≥ memmap_threshold_kb) → if indexed OR any input has deferred points, upgrade dense configs to HNSW + quantization → resolve each dense vector's memory placement (explicit `memory` / deprecated `on_disk` fallback) and map it to a storage type (Cold ⇒ Mmap; Cached/Pinned ⇒ InRamMmap only under the single_file_mmap feature flag, else in-RAM wins; unset ⇒ Mmap when the on-disk threshold tripped) → pick the sparse index type by big/small × placement → build the `SegmentBuilder` under temp_path.
**Invariant:** (1) deferred points MUST force an HNSW index even below the indexing threshold — promotion of deferred (invisible) points requires an index to land in; (2) the sizing basis is the largest per-name vector store, not total bytes — one huge name must trigger the thresholds even if others are small; (3) explicit user placement requests beat threshold-derived defaults, but the feature flag can still downgrade in-RAM requests to InRamMmap; (4) only explicitly-requested fields are persisted into the new segment's index config, keeping legacy-only configurations byte-identical for cross-version loading.
**Probe:** no dedicated unit test drives `optimized_segment_builder` alone (test gap recorded); the indexing-threshold path is exercised end-to-end by `lib/collection/src/collection_manager/optimizers/indexing_optimizer.rs::test_indexing_optimizer_with_number_of_segments` (:706-783, signature + doc read), and the builder's proxy-rejection and threshold logic are pinned by direct read of :163-377.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "optimized_segment_builder threshold_is_indexed any_has_deferred memmap_threshold_kb SparseIndexType", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the threshold-on-largest-name sizing, the deferred-points-force-index rule, the placement-ladder precedence (explicit request > threshold default > feature-flag downgrade), and the persist-only-explicit-fields compatibility rule. Adapt the storage-type enum to your host's backends. Omit the deprecated `on_disk` fallback unless you carry a legacy config surface.
