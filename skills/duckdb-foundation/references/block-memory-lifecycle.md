<!-- capsule-v2 -->
# BlockMemory lifecycle — what must happen when a block's memory object is created, changed, and destroyed?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** Which invariants govern BlockMemory state transitions (unload, resize, destroy) and the dead-node repair in the destructor?

## Two constructors, unsigned-overflow resize trick, destructor repairs queue accounting
**Path/Symbol:** `src/storage/buffer/block_handle.cpp` — ctors :13-31, `~BlockMemory` (:33-56), `ChangeMemoryUsage` (:66-74), `ResizeBuffer` (:99-107), `CanUnload` (:109-123), `UnloadAndTakeBlock` (:127-145).
**Signature:** `void ChangeMemoryUsage(BlockLock&, int64_t delta)` with `D_ASSERT(delta < 0)`; `bool CanUnload() const`; dtor calls `GetBufferPool().IncrementDeadNodes(*this)` when it still owns a live queue entry.
**Data Shape:** fields initialized once: `state=BLOCK_UNLOADED`, `readers=0`, `eviction_seq_num(0)`, `has_queue_entry(false)`, `eviction_queue_idx(INVALID_INDEX)`, default policy `DestroyBufferUpon::BLOCK`.

### Decisive source
```cpp
// ChangeMemoryUsage: negative delta via defined unsigned wraparound
// FIXME: Too clever ATM. The crux here is that the unsigned overflow is defined.
// FIXME: It overflows twice to lead to the correct subtraction.
D_ASSERT(delta < 0);
memory_usage += static_cast<idx_t>(delta);
GetMemoryCharge().Resize(GetMemoryUsage());

// ~BlockMemory: the weak pointer in the queue entry can become unlockable before this
// destructor body runs, so a queue consumer can briefly decrement before this increment.
if (HasLiveQueueEntry() && GetBufferType() != FileBufferType::TINY_BUFFER)
    GetBufferManager().GetBufferPool().IncrementDeadNodes(*this);   // repairs final count
```

**Flow:** load path pins readers and swaps buffers; unload writes temp file when the block is beyond MAXIMUM_BLOCK and policy demands it; destruction first nulls swizzling pointers, then repairs eviction-queue accounting, then releases the memory charge if still loaded.
**Invariant:** TINY_BUFFERs never participate in dead-node counting; every buffer mutation happens under the block lock (`VerifyMutex(l)` at each entry) and keeps `memory_usage == buffer->AllocSize()` true at the end of ResizeBuffer.
**Probe:** `grep -c 'This increment repairs the final count for that expired live entry' src/storage/buffer/block_handle.cpp` → `1`; `grep -c 'It overflows twice to lead to the correct subtraction' src/storage/buffer/block_handle.cpp` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "BlockMemory CanUnload UnloadAndTakeBlock ChangeMemoryUsage IncrementDeadNodes", limit: 10 });
```

## Verdict
Adopt lock-verified state transitions plus the destructor-side accounting repair; adapt the unsigned-wrap trick only if you keep idx_t sizes; omit swizzling if your blocks are never pointer-patched in place.
