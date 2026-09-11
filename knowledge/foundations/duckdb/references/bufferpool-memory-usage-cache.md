<!-- capsule-v2 -->
# Memory usage accounting — how do you keep a global memory counter cheap on many-core machines?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How is per-tag memory tracked with atomics only, and why are small updates cached per CPU?

## Per-CPU cache slots flush to global counters at 32 KiB
**Path/Symbol:** `src/storage/buffer/buffer_pool.cpp:BufferPool::MemoryUsage::UpdateUsedMemory` (:584-610); constants in `buffer_pool.hpp` :131-134 — `MEMORY_USAGE_CACHE_COUNT = 64`, `MEMORY_USAGE_CACHE_THRESHOLD = 32 << 10`, `TOTAL_MEMORY_USAGE_INDEX = MEMORY_TAG_COUNT`.
**Signature:** `void UpdateUsedMemory(MemoryTag tag, int64_t size)`; slot chosen by `TaskScheduler::GetEstimatedCPUId() % MEMORY_USAGE_CACHE_COUNT` (:591).
**Data Shape:** `MemoryUsageCounters = array<atomic<int64_t>, MEMORY_TAG_COUNT + 1>` (extra slot = total); documented drift bound: "maximum difference between memory statistics and actual usage is 2MB (64 * 32k)".

### Decisive source
```cpp
if ((idx_t)AbsValue(size) < MEMORY_USAGE_CACHE_THRESHOLD) {
    auto cache_idx  = (idx_t)TaskScheduler::GetEstimatedCPUId() % MEMORY_USAGE_CACHE_COUNT;
    auto new_tag_size = cache[tag_idx].fetch_add(size, relaxed) + size;
    if ((idx_t)AbsValue(new_tag_size) >= MEMORY_USAGE_CACHE_THRESHOLD)
        memory_usage[tag_idx].fetch_add(cache[tag_idx].exchange(0, relaxed), relaxed);
    // ... same pattern for the TOTAL slot ...
} else {
    // big updates go straight to the global counters
    memory_usage[tag_idx].fetch_add(size, relaxed);
    memory_usage[TOTAL_MEMORY_USAGE_INDEX].fetch_add(size, relaxed);
}
```

**Flow:** small alloc/free → add into this CPU's cache slots → when a slot crosses ±32 KiB, exchange-to-zero and fold it into the global tag/total counters → eviction checks read the NO_FLUSH view, admin reads can request FLUSH.
**Invariant:** both the per-tag AND total cache slots must be folded independently (they cross their thresholds separately); every path must update the TOTAL slot exactly once per call or accounting drifts monotonically.
**Probe:** `grep -c 'fetch_add(size, std::memory_order_relaxed)' src/storage/buffer/buffer_pool.cpp` → `4`; `grep -c 'exchange(0, std::memory_order_relaxed)' src/storage/buffer/buffer_pool.cpp` → `2`; `grep -n 'GetEstimatedCPUId() % MEMORY_USAGE_CACHE_COUNT' src/storage/buffer/buffer_pool.cpp` → :591.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "UpdateUsedMemory MemoryUsage MEMORY_USAGE_CACHE_THRESHOLD GetEstimatedCPUId", limit: 10 });
```

## Verdict
Adopt CPU-pinned cache slots with threshold flush as a sharded counter that avoids global cacheline ping-pong; adapt the threshold/ratio to your accuracy needs; omit jemalloc-derived CPU detection if your runtime offers a native tid.
