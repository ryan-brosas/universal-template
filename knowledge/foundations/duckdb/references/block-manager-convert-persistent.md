<!-- capsule-v2 -->
# ConvertToPersistent — how do you turn a transient buffer into a durable on-disk block without losing concurrent readers?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the safe sequence for registering the persistent block, copying in THREAD_SAFE mode, writing to disk, and re-queuing?

## Copy-or-destructive conversion; readers>1 veto; uncontended lock for requeue
**Path/Symbol:** `src/storage/buffer/block_manager.cpp:BlockManager::ConvertToPersistent` (:58-118); mode enum `block_manager.hpp:27` — `{ DESTRUCTIVE, THREAD_SAFE }`.
**Signature:** `shared_ptr<BlockHandle> ConvertToPersistent(QueryContext, block_id_t, shared_ptr<BlockHandle> old_block, BufferHandle old_handle, ConvertToPersistentMode mode)`.
**Data Shape:** new block starts `BLOCK_UNLOADED`, readers 0; old buffer must satisfy `AllocSize() <= GetBlockAllocSize()` ("Temp buffers can be larger than the storage block size. But persistent buffers cannot.").

### Decisive source
```cpp
auto new_block = RegisterBlock(block_id);
D_ASSERT(new_block->GetMemory().GetState() == BlockState::BLOCK_UNLOADED);
if (mode == ConvertToPersistentMode::THREAD_SAFE) {   // copy: others keep using old block
    auto old_block_copy = buffer_manager.AllocateMemory(old_block->GetMemory().GetMemoryTag(), this, false);
    auto copy_pin = buffer_manager.Pin(old_block_copy);
    memcpy(copy_pin.GetDataMutable(), old_handle.Ptr(), GetBlockSize());
    ...
}
if (old_block_memory.GetReaders() > 1)
    throw InternalException("... cannot be called for block %d as old_block has multiple readers active", ...);
Write(context, *converted_buffer, block_id);
old_block_memory.ConvertToPersistent(lock, *new_block, std::move(converted_buffer));
lock.unlock();  old_handle.Destroy();  old_block.reset();     // release BEFORE requeue
// AddToEvictionQueue requires the block lock. new_block was just created here → uncontended.
purge_queue = buffer_manager.GetBufferPool().AddToEvictionQueue(new_lock, new_block);
```

**Flow:** register target id → optional defensive copy → veto multi-reader destructive conversion → write payload to storage → swap state/buffer into the new block under its lock → drop ALL old-side locks/handles → enqueue the now-unpinned new block and optionally purge.
**Invariant:** locks are released before AddToEvictionQueue's own lock acquisition except the freshly created (uncontended) new-block lock; disk write happens BEFORE the in-memory conversion so a crash leaves no half-converted block.
**Probe:** `grep -c 'ConvertToPersistentMode::THREAD_SAFE' src/storage/buffer/block_manager.cpp` → `1`; `grep -n 'lock.unlock()' src/storage/buffer/block_manager.cpp` → :103; `grep -c 'multiple readers active' src/storage/buffer/block_manager.cpp` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "ConvertToPersistent RegisterBlock ConvertToPersistentMode THREAD_SAFE AddToEvictionQueue", limit: 10 });
```

## Verdict
Adopt the register→write→convert→requeue ordering with reader vetoes; adapt your durability boundary; omit THREAD_SAFE copying if callers already guarantee exclusivity.
