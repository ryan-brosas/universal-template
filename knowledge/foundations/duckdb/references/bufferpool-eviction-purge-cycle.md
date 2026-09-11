<!-- capsule-v2 -->
# Eviction queue purge — how do you garbage-collect a concurrent FIFO without stopping producers?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does the purge cycle amortize dead-node cleanup while preserving approximate-LRU order?

## Every 4096 inserts, one purger, bulk dequeue + token-paired re-enqueue
**Path/Symbol:** `src/storage/buffer/buffer_pool.cpp:EvictionQueue::AddToEvictionQueue` (:144-147), `Purge` (:154-213), `PurgeIteration` (:215-251); constants :115-124.
**Signature:** `bool AddToEvictionQueue(BufferEvictionNode&&)` (returns "purge now"); `void Purge()`; `void PurgeIteration(const idx_t purge_size)`.
**Data Shape:** constants: `INSERT_INTERVAL=4096`, `PURGE_SIZE_MULTIPLIER=2`, `EARLY_OUT_MULTIPLIER=4`, `ALIVE_NODE_MULTIPLIER=4`; reusable scratch vector `purge_nodes`; dedicated consumer+producer tokens for the moodycamel queue.

### Decisive source
```cpp
// trigger: every INSERT_INTERVAL insertions
return ++evict_queue_insertions % INSERT_INTERVAL == 0;
// single-thread gate:
unique_lock<mutex> guard(purge_lock, std::try_to_lock);
if (!guard.owns_lock()) return;
// adaptive loop exits (any of): size < purge*EARLY_OUT | alive*(MULT-1) > dead | max_purges==0
const idx_t actually_dequeued = q.try_dequeue_bulk(purge_consumer_token, purge_nodes.begin(), purge_size);
...
purge_nodes[alive_count++] = std::move(node);      // compact alive to front
q.enqueue_bulk(purge_producer_token, purge_nodes.begin(), alive_count);
```

**Flow:** insertion counter hits 4096 → caller invokes Purge → loser threads early-out on try-lock → winner bulk-dequeues 8192 nodes, splits dead/alive in one pass, decrements the dead counter by what it reclaims, and re-enqueues survivors via its producer token into a sub-queue the consumer token has already passed (order preserved).
**Invariant:** only ONE thread purges at a time (`try_to_lock`, never blocks); alive nodes are re-enqueued through the paired producer token so they cannot starve the consumer token's position; `total_dead_nodes -= dead_count` happens exactly once per reclaimed node.
**Probe:** `grep -c 'INSERT_INTERVAL' src/storage/buffer/buffer_pool.cpp` → `8`; `grep -n 'std::try_to_lock' src/storage/buffer/buffer_pool.cpp` → :156; `grep -c 'q.enqueue_bulk(purge_producer_token' src/storage/buffer/buffer_pool.cpp` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "PurgeIteration Purge AddToEvictionQueue purge_consumer_token enqueue_bulk", limit: 10 });
```

## Verdict
Adopt the interval-triggered, try-lock-gated, token-symmetric bulk purge; adapt batch size ratios to your workload; omit the debug sleep injection used for race testing.
