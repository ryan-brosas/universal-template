<!-- capsule-v2 -->
# Buffer allocator bridge — how does DuckDB route its global allocator through buffer-pool accounting?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How do Allocate/Free/Realloc callbacks keep MemoryTag::ALLOCATOR charges balanced, including the manual-reservation hack?

## Evict-on-allocate; Free builds a zeroed reservation to subtract; Realloc resizes through one
**Path/Symbol:** `src/storage/standard_buffer_manager.cpp` — `BufferAllocatorData` (:38-41), `BufferAllocatorAllocate` (:736-745), `BufferAllocatorFree` (:746-753), `BufferAllocatorRealloc` (:754-763); wired in ctor :74-75.
**Signature:** `static data_ptr_t BufferAllocatorAllocate(PrivateAllocatorData*, idx_t size)`; free/realloc mirror malloc-family signatures.
**Data Shape:** `BufferPoolReservation r(MemoryTag::ALLOCATOR, pool); r.size = size; r.Resize(0);` — constructs a reservation AT the size then shrinks it to zero so the pool's accounting sees −size without ever having memory.

### Decisive source
```cpp
auto reservation = data.manager.EvictBlocksOrThrow(QueryContext(), MemoryTag::ALLOCATOR, size, nullptr,
                                                   "failed to allocate data of size %s%s", ...);
// We rely on manual tracking of this one. :(
reservation.size = 0;                       // charge already counted via eviction pass
return Allocator::Get(data.manager.db).AllocateData(size);
...
void StandardBufferManager::BufferAllocatorFree(...) {
    BufferPoolReservation r(MemoryTag::ALLOCATOR, data.manager.GetBufferPool());
    r.size = size;
    r.Resize(0);                            // net effect: UpdateUsedMemory(ALLOCATOR, -size)
```

**Flow:** alloc: evict until the ALLOCATOR tag has room → hand out bytes from the underlying allocator (the pool-side reservation is discarded because frees don't round-trip a token) → free: fabricate a size-charged reservation and Resize(0) to return the credit → realloc: no-op when sizes match, else resize old→new through one temporary reservation.
**Invariant:** every byte allocated under this allocator is eventually balanced by exactly one fabricated-reservation release; skipping the Resize dance would permanently leak ALLOCATOR-tagged accounting and wedge future evictions.
**Probe:** `grep -c 'We rely on manual tracking of this one' src/storage/standard_buffer_manager.cpp` → `1`; `grep -c "r.size = size;" src/storage/standard_buffer_manager.cpp` → `1` (free) plus realloc variant `r.size = old_size`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "BufferAllocatorAllocate BufferAllocatorFree BufferAllocatorRealloc BufferAllocatorData", limit: 10 });
```

## Verdict
Adopt callback-shaped allocator hooks with explicit accounting balance; adapt if your allocator supports user-data tokens natively; omit the realloc shortcut only when sizes are always padded.
