<!-- capsule-v2 -->
# Eviction entry point — how does an allocation evict victims, reuse their memory, and fall back to the object cache?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the contract of `EvictBlocks` — queue order, buffer hand-back, reservation semantics, and the object-cache last resort?

## Queue-order eviction with exact-size block recycling; object cache only after all queues fail
**Path/Symbol:** `src/storage/buffer/buffer_pool.cpp:EvictBlocks` (:377-389), `EvictBlocksInternal` (:391-432), `EvictObjectCacheEntries` (:345-375).
**Signature:** `EvictionResult EvictBlocks(QueryContext, MemoryTag tag, idx_t extra_memory, idx_t memory_limit, unique_ptr<FileBuffer> *buffer = nullptr)`; `struct EvictionResult { bool success; TempBufferPoolReservation reservation; }`.
**Data Shape:** `TempBufferPoolReservation` RAII-reserves `extra_memory` up front and `Resize(0)`s itself on failure; passing a non-null `buffer` requests memory reuse.

### Decisive source
```cpp
for (auto &queue : queues) {                       // cheap-free → write-back → tiny
    auto block_result = EvictBlocksInternal(context, *queue, tag, extra_memory, memory_limit, buffer);
    if (block_result.success) return block_result;
}
return EvictObjectCacheEntries(tag, extra_memory, memory_limit);   // metadata/config cache last

// inside one queue:
if (memory_usage.GetUsedMemory(NO_FLUSH) <= memory_limit) { /* already fine */ }
queue.IterateUnloadableBlocks([&](BufferEvictionNode&, const shared_ptr<BlockMemory> &handle, BlockLock &lock) {
    if (buffer && handle->GetBuffer(lock)->AllocSize() == extra_memory) {
        *buffer = handle->UnloadAndTakeBlock(lock, context);   // steal the exact-sized block
        found = true; return false;
    }
    handle->Unload(lock, context);
    if (memory_usage.GetUsedMemory(NO_FLUSH) <= memory_limit) { found = true; return false; }
    return true;                                                // keep scanning
});
if (!found) r.Resize(0);                                       // release the failed reservation
```

**Flow:** reserve → under-limit? succeed instantly (plus allocator flush if above threshold) → else walk queues unloading victims until the limit holds or queues are dry → still over? evict object-cache entries in a loop until freed==0 → failure collapses the reservation so callers see no charge.
**Invariant:** the reservation is taken BEFORE any victim is touched and shrunk on failure — allocation either fully succeeds or fully unwinds; buffer reuse requires an EXACT AllocSize match (`== extra_memory`), never approximate.
**Probe:** `grep -c 'EvictBlocks' src/storage/buffer/buffer_pool.cpp` → `5`; `grep -c 'r.Resize(0)' src/storage/buffer/buffer_pool.cpp` → `2`; `grep -c 'object_cache->EvictToReduceMemory' src/storage/buffer/buffer_pool.cpp` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "EvictBlocks EvictBlocksInternal EvictObjectCacheEntries TempBufferPoolReservation", limit: 10 });
```

## Verdict
Adopt reserve-then-evict with exact-size recycling as the allocation fast path; adapt which caches are consulted last; omit QueryContext plumbing if your engine has no per-query context object.
