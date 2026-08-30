<!-- capsule-v2 -->
# Age-based block purge — how do you evict by age when the queue is not a true LRU?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does `PurgeAgedBlocks` unload stale blocks while keeping the extension-facing contract that depends on it?

## Timestamp-bounded scan: unload unconditionally, stop at the freshness frontier
**Path/Symbol:** `src/storage/buffer/buffer_pool.cpp:PurgeAgedBlocks` (:436-446), `PurgeAgedBlocksInternal` (:448-462); timestamps written in `AddToEvictionQueue` path :288-292; guarded method comment :434-435.
**Signature:** `idx_t PurgeAgedBlocks(uint32_t max_age_sec)` — returns purged bytes; per-block predicate `bool is_fresh = lru_timestamp_msec >= limit && lru_timestamp_msec <= now`.
**Data Shape:** LRU timestamps are `steady_clock` milliseconds stored on the block (`SetLRUTimestamp`), captured only when `track_eviction_timestamps` is enabled in the pool constructor.

### Decisive source
```cpp
// Do not remove this method. There are extensions that rely on time-based
// purging of blocks, that uses the method.
queue.IterateUnloadableBlocks([&](BufferEvictionNode&, const shared_ptr<BlockMemory> &handle, BlockLock &lock) {
    // We will unload this block regardless. But stop the iteration immediately afterward
    // if this block is younger than the age threshold.
    auto lru_timestamp_msec = handle->GetLRUTimestamp();
    bool is_fresh = lru_timestamp_msec >= limit && lru_timestamp_msec <= now;
    purged_bytes += handle->GetMemoryUsage();
    handle->Unload(lock);
    return !is_fresh;                    // false stops the walk at the fresh frontier
});
```

**Flow:** compute now/limit once → for each queue walk unloadable blocks → unload every visited block (counting bytes) → halt the whole queue walk at the first block whose timestamp is inside the window.
**Invariant:** the upper bound `lru_timestamp <= now` defends against clock skew making FUTURE timestamps look infinitely old; blocks without recorded timestamps (tracking disabled) are treated as epoch 0 ⇒ always "not fresh" ⇒ never purge-stopped early.
**Probe:** `grep -n 'bool is_fresh = lru_timestamp_msec >= limit && lru_timestamp_msec <= now' src/storage/buffer/buffer_pool.cpp` → :455; `grep -c 'PurgeAgedBlocks' src/storage/buffer/buffer_pool.cpp` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "PurgeAgedBlocks PurgeAgedBlocksInternal GetLRUTimestamp SetLRUTimestamp", limit: 10 });
```

## Verdict
Adopt the monotonic-clock age sweep with frontier stop for TTL-style cache trimming; adapt the timestamp source; keep the "unload then test" ordering only if your consumers tolerate it — DuckDB documents this as an extension-compatibility surface.
