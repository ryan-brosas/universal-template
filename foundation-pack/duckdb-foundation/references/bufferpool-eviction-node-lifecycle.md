<!-- capsule-v2 -->
# Eviction node lifecycle — how does a lock-free LRU queue stay correct when entries go stale?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How do weak pointers + monotonic sequence numbers + a has-live-entry flag cooperate so dead nodes are counted exactly once?

## weak_ptr + eviction_seq_num + has_queue_entry; dead accounting on both ends
**Path/Symbol:** `src/storage/buffer/buffer_pool.cpp:BufferEvictionNode` (:42-59); `AddToEvictionQueue` (:271-298); `IterateUnloadableBlocks` (:464-510); `BlockMemory` fields in `block_handle.hpp` — `atomic<idx_t> eviction_seq_num` (:231), `bool has_queue_entry` (:235).
**Signature:** `bool BufferEvictionNode::IsDeadNode(optional_idx)`; `idx_t BlockMemory::NextEvictionSequenceNumber() { return ++eviction_seq_num; }`; `void SetHasLiveQueueEntry(BlockLock&, bool)`.
**Data Shape:** queue holds `weak_ptr<BlockMemory>` + the seq number captured at enqueue; `has_queue_entry` is lock-guarded EXCEPT in the destructor (exclusive ownership).

### Decisive source
```cpp
// AddToEvictionQueue: count a superseded live entry BEFORE bumping the sequence number
if (memory.HasLiveQueueEntry(lock)) {
    // PurgeIteration reads sequence numbers without the block lock; bumping first could
    // let it see the previous entry as stale and decrement before this matching increment.
    queue.IncrementDeadNodes();
}
auto ts = memory.NextEvictionSequenceNumber();
...
// IterateUnloadableBlocks: consumer side of exactly-once dead counting
if (node.handle_sequence_number != handle->GetEvictionSequenceNumber()) {
    DecrementDeadNodes(); continue;            // newer entry exists: this one is dead
}
handle->SetHasLiveQueueEntry(lock, false);     // live entry consumed: no dead-count, no decrement
if (!handle->CanUnload()) continue;            // pinned: gets a NEW entry on unpin
```

**Flow:** unpin → verify readers==0 → if an old live entry exists count it dead → bump seq → push node → set flag; consumer pops → stale (seq mismatch) ⇒ dead--; current ⇒ clear flag and try unload; destructor path counts its own live entry as dead (TINY_BUFFER excepted) because "the weak pointer can become unlockable before this destructor body runs".
**Invariant:** `IncrementDeadNodes`/`DecrementDeadNodes` must pair per QUEUE ENTRY (not per block): every stale dequeue decrements exactly what some enqueue incremented; the increment-before-bump ordering closes the race where purge reads the old seq unlocked.
**Probe:** `grep -c 'DecrementDeadNodes' src/storage/buffer/buffer_pool.cpp` → `3`; `grep -c 'SetHasLiveQueueEntry' src/storage/buffer/buffer_pool.cpp` → `2` (:293 true, :499 false).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "BufferEvictionNode IsDeadNode IterateUnloadableBlocks NextEvictionSequenceNumber", limit: 10 });
```

## Verdict
Adopt seq-number staleness detection with paired dead-node counters for any lock-free second-chance list; adapt to std::weak_ptr semantics you already have; omit the debug sleep hooks (`debug_eviction_queue_sleep`) outside tests.
