<!-- capsule-v2 -->
# Eviction queue selection — why are there 8 queues and how is a block routed to one?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does the buffer pool turn a single LRU into per-buffer-type queues, and where does the "front vs back" trick live?

## Three type classes × per-class queue counts; index math makes idx=0 hottest
**Path/Symbol:** `src/storage/buffer/buffer_pool.cpp:GetEvictionQueueForBlockMemory` (:300-319); constructor :253-267; sizes from `buffer_pool.hpp` — `BLOCK_AND_EXTERNAL_FILE_QUEUE_SIZE = 1`, `MANAGED_BUFFER_QUEUE_SIZE = 6`, `TINY_BUFFER_QUEUE_SIZE = 1` (:118-120).
**Signature:** `EvictionQueue &BufferPool::GetEvictionQueueForBlockMemory(const BlockMemory &memory)`; `static idx_t FileBufferTypeToEvictionQueueTypeIdx(const FileBufferType&)` (:15-27).
**Data Shape:** BLOCK/EXTERNAL_FILE → class 0 ("cheap, just free"), MANAGED_BUFFER → class 1 ("have to write to storage"), TINY_BUFFER → class 2 ("last resort"); optional `eviction_queue_idx` (set-once, MANAGED_BUFFER only) picks a sub-queue.

### Decisive source
```cpp
idx_t queue_index = 0;
const auto handle_queue_type_idx = FileBufferTypeToEvictionQueueTypeIdx(handle_buffer_type);
for (idx_t type_idx = 0; type_idx < handle_queue_type_idx; type_idx++)
    queue_index += eviction_queue_sizes[type_idx];
const auto &queue_size = eviction_queue_sizes[handle_queue_type_idx];
auto eviction_queue_idx = memory.GetEvictionQueueIndex();
if (eviction_queue_idx < queue_size)
    queue_index += queue_size - eviction_queue_idx - 1;   // idx==0 → LAST slot (hottest), >=size → first
```

**Flow:** eviction walks queues in array order (:379-384) — free-able blocks first, then write-back buffers, tiny buffers last; within the MANAGED class, lower configured `eviction_queue_idx` ⇒ closer to the dequeue end ⇒ evicted sooner.
**Invariant:** routing is pure arithmetic on immutable sizes — no locks needed to pick a queue; `GetEvictionQueueIndex()` defaults to INVALID and is clamped by the `< queue_size` check so unset blocks land in the coldest slot.
**Probe:** `grep -c 'eviction_queue_sizes' src/storage/buffer/buffer_pool.cpp` → `7`; `grep -n 'queue_index += queue_size - eviction_queue_idx - 1' src/storage/buffer/buffer_pool.cpp` → :314.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "GetEvictionQueueForBlockMemory EvictionQueue FileBufferTypeToEvictionQueueTypeIdx", limit: 10 });
```

## Verdict
Adopt class-stratified FIFO queues with front-is-coldest index math as an O(1) eviction-priority scheme; adapt class counts to your buffer taxonomy; omit DuckDB's specific external-file-cache class if unused.
