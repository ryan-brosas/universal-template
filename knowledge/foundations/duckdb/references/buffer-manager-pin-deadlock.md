<!-- capsule-v2 -->
# Pin deadlock avoidance — how do you pin a block without risking self-deadlock on handle destruction?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** Why does `StandardBufferManager::Pin` drop the block lock before returning, and what re-check follows eviction?

## Scope-exit hazard documented in-source; lock-drop + re-check-after-evict
**Path/Symbol:** `src/storage/standard_buffer_manager.cpp:Pin` (:338-378) — comment :339-342; retry loop :360-367; loaded fast-path return :356.
**Signature:** `BufferHandle Pin(const QueryContext&, shared_ptr<BlockHandle> &handle)`; internally `EvictBlocksOrThrow(...)` with `"failed to pin block of size %s%s"`.
**Data Shape:** `required_memory` is read UNDER the block lock; the actual load happens after re-acquiring; the returned `BufferHandle` owns one reader count.

### Decisive source
```cpp
// we need to be careful not to return the BufferHandle to this block while holding the
// BlockHandle's lock as exiting this function's scope may cause the destructor of the
// BufferHandle to be called while holding the lock — the destructor calls Unpin, which
// grabs the BlockHandle's lock again, causing a deadlock
{
    auto lock = block_memory.GetLock();
    if (block_memory.GetState() == BlockState::BLOCK_LOADED)
        buf = handle->Load(context);
    required_memory = block_memory.GetMemoryUsage();
}
if (buf.IsValid()) return buf;   // already-loaded: return WITHOUT holding the lock
... EvictBlocksOrThrow(...) ...
// lock the handle again and repeat the check (in case anybody loaded in the meantime)
```

**Flow:** take lock briefly → loaded? bump readers and return → else capture size, release lock → evict room for it → re-lock → if another thread loaded it meanwhile, drop our reservation (`Resize(0)`) and use theirs → otherwise load with the recycled buffer and adjust accounting by the alloc-size delta.
**Invariant:** the block lock is NEVER held while constructing/destroying a BufferHandle outside the guarded scope; after eviction you must re-check state under the lock because loaders race lock-free between the two critical sections.
**Probe:** `grep -c 'as exiting this function.s scope may cause the destructor of the BufferHandle' src/storage/standard_buffer_manager.cpp` → `1`; `grep -c 'reservation.Resize(0)' src/storage/standard_buffer_manager.cpp` → `3`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "StandardBufferManager Pin EvictBlocksOrThrow repeat the check reusable_buffer", limit: 10 });
```

## Verdict
Adopt the narrow-critical-section pin with post-eviction recheck; adapt error text; omit the encrypted/temp-file branches unless your storage offloads blocks the same way.
