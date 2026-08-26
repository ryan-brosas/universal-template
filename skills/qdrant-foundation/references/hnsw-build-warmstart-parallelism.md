<!-- capsule-v2 -->
# HNSW build warm start — how do you parallelize graph inserts without disconnecting the graph?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `ext-qdrant`. **Question:** A porter parallelizing HNSW inserts must know why the first N points are inserted single-threaded and where deleted points are excluded.

## Parallel insert with single-threaded warm start
**Path/Symbol:** `lib/segment/src/index/hnsw_index/hnsw/build.rs`: `HNSWIndex::build` (:53-598), `insert_point` closure (:329-348), `build_filtered_graph` (:631-716); threshold in `hnsw.rs` :33-38.
**Signature:** `fn build(open_args: HnswIndexOpenArgs<'_>, build_args: VectorIndexBuildArgs<'_, R>) -> OperationResult<Self>`; threshold `SINGLE_THREADED_HNSW_BUILD_THRESHOLD` = 32 (debug) / 256 (release).
**Data Shape:** input: internal point ids from `id_tracker.point_mappings().iter_internal_excluding(deleted_bitslice)`; per-point work = `FilteredScorer::new_internal(...)` + `graph_layers_builder.link_new_point(vector_id, points_scorer)`; output: populated `GraphLayersBuilder`.

### Decisive source
```rust
/// Build first N points in HNSW graph using only a single thread, to avoid
/// disconnected components in the graph.
pub const SINGLE_THREADED_HNSW_BUILD_THRESHOLD: usize = 256; // release; 32 in debug

let first_few_ids = Vec::with_capacity(SINGLE_THREADED_HNSW_BUILD_THRESHOLD);
// ...
for vector_id in first_few_ids { insert_point(vector_id)?; }          // serial seed
if !ids.is_empty() {
    pool.install(|| ids.into_par_iter().try_for_each(insert_point))?; // parallel body
}
```
And inside `build_filtered_graph` (the payload-block twin of the same pattern):
```rust
// First index points in single thread so ensure warm start for parallel indexing process
for point_id in points_to_index[..first_points].iter().copied() { insert_points(point_id)?; }
// Once initial structure is built, index remaining points in parallel
// So that each thread will insert points in different parts of the graph,
// it is less likely that they will compete for the same locks
pool.install(|| points_to_index.into_par_iter().skip(first_points).try_for_each(insert_points))?;
```

**Flow:** deleted bitslice obtained once from vector storage → ids iterated *excluding deleted* (deletion never enters the builder) → first ≤256 ids inserted serially to grow one connected component → remainder via rayon `into_par_iter` on a dedicated low-priority pool (`linux_low_thread_priority`, thread name `hnsw-build-{idx}`) → progress counter incremented per point (`AtomicU64`, Relaxed).
**Invariant:** (1) the warm-start prefix MUST be inserted before any parallel insert or early-arriving threads can form disconnected components that layer-above search cannot bridge; (2) deleted points must be excluded at the id iterator, not filtered after scoring; (3) per-insert stop checks (`check_process_stopped`) run inside the closure, not between batches; (4) the hardware counter is `disposable()` for internal builds — never bill user queries' IO/comparison budgets here.

**Probe:** `grep -c "SINGLE_THREADED_HNSW_BUILD_THRESHOLD" lib/segment/src/index/hnsw_index/hnsw.rs lib/segment/src/index/hnsw_index/hnsw/build.rs` → prints per-file lines: `hnsw.rs:2` and `build.rs:5` (multi-file grep counts LINES per file — sum them). Direct tests: `lib/segment/tests/integration/hnsw_discover_test.rs::filtered_hnsw_discover_precision` (:171) and search-precision suites pin resulting-graph behavior end-to-end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-qdrant", query: "SINGLE_THREADED_HNSW_BUILD_THRESHOLD link_new_point FilteredScorer new_internal", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the warm-start-then-parallel ordering, iterator-level deleted exclusion, and disposable counters for internal builds. Adapt the executor (rayon pool + Linux nice priority is host-specific). Omit GPU graph construction (`gpu_build` feature) when porting the CPU path. Coverage caveat: no unit test pins the constant's value directly; behavior is pinned by integration precision tests.
