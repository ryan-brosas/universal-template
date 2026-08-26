<!-- capsule-v2 -->
# BlockHandle registry — how do you share one cached block handle among readers using weak pointers?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does the block manager cache handles without keeping them alive, and how are expired entries detected?

## unordered_map<block_id, weak_ptr>; find→lock→reuse; erase on unregister
**Path/Symbol:** `src/storage/buffer/block_manager.cpp` — `BlockIsRegistered` (:16-25), `TryGetBlock` (:28-39), `RegisterBlock` (:41-56), `UnregisterBlock` (:128-133); map decl `block_manager.hpp:194` — `unordered_map<block_id_t, weak_ptr<BlockHandle>> blocks;`.
**Signature:** `shared_ptr<BlockHandle> RegisterBlock(block_id_t)` — returns the live handle or creates + registers; all three readers take `lock_guard<mutex> lock(blocks_lock)`.
**Data Shape:** value type is `weak_ptr<BlockHandle>` so dropping the last external reference frees the BlockMemory even though the id stays mapped.

### Decisive source
```cpp
auto entry = blocks.find(block_id);
if (entry != blocks.end()) {
    auto existing_ptr = entry->second.lock();   // may be expired
    if (existing_ptr) return existing_ptr;      // "it hasn't [expired]! return it"
}
auto result = make_shared_ptr<BlockHandle>(*this, block_id, MemoryTag::BASE_TABLE);
blocks[block_id] = weak_ptr<BlockHandle>(result);   // register as weak pointer
```

**Flow:** query path: find → `expired()`/`lock()` decides liveness → register path: same find, create only on miss → teardown: `UnregisterBlock` erases under `blocks_lock`; during manager destruction `in_destruction=true` skips unregistration entirely ("flip the flag to not perform UnregisterBlock on the block manager that is being destructed").
**Invariant:** every access to `blocks` happens under `blocks_lock`; liveness is determined by `weak_ptr::lock()` never by presence in the map.
**Probe:** `grep -c 'blocks.find' src/storage/buffer/block_manager.cpp` → `3`; `grep -c 'blocks_lock' src/storage/buffer/block_manager.cpp` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "RegisterBlock TryGetBlock BlockIsRegistered UnregisterBlock blocks_lock", limit: 10 });
```

## Verdict
Adopt weak-value caching for shared resource handles; adapt key/id types; omit the in_destruction flag if your shutdown ordering cannot reach re-registration.
