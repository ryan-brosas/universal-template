<!-- capsule-v2 -->
# BufferHandle RAII pin — what does a pin own, and how does dropping it unpin exactly once?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How is the pin/unpin pair made exception- and move-safe?

## Move-only handle; Destroy() unpins via the manager; IsValid == node != nullptr
**Path/Symbol:** `src/storage/buffer/buffer_handle.cpp` (whole file, 62L); header `buffer_handle.hpp:18-63`.
**Signature:** `BufferHandle(shared_ptr<BlockHandle>, optional_ptr<FileBuffer>)`; `void Destroy()` → `handle->GetMemory().GetBufferManager().Unpin(handle)`; `bool IsValid() const { return node != nullptr; }`; copy ctor/assign deleted, moves swap.
**Data Shape:** holds BOTH the shared handle (keeps BlockMemory alive) and an `optional_ptr<FileBuffer>` node (the actual buffer view).

### Decisive source
```cpp
BufferHandle::BufferHandle(BufferHandle &&other) noexcept : node(nullptr) {
    std::swap(node, other.node);
    std::swap(handle, other.handle);
}
BufferHandle::~BufferHandle() { Destroy(); }
void BufferHandle::Destroy() {
    if (!handle || !IsValid()) return;              // idempotent
    handle->GetMemory().GetBufferManager().Unpin(handle);   // reader-- + maybe evict-queue add
    handle.reset();
    node = nullptr;
}
```

**Flow:** Pin returns a valid handle (+1 reader) → caller reads via `Ptr()/GetDataMutable()` (both assert validity) → scope exit or explicit Destroy calls Unpin through the manager — never touching block state directly.
**Invariant:** unpinning must route through the BufferManager (which owns eviction decisions), not mutate readers directly; double-Destroy is safe because both fields are nulled after the first call.
**Probe:** `grep -c 'std::swap(node, other.node)' src/storage/buffer/buffer_handle.cpp` → `2` (move ctor + move assign); `grep -c 'GetBufferManager().Unpin(handle)' src/storage/buffer/buffer_handle.cpp` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "BufferHandle Destroy Unpin IsValid GetBlockHandle", limit: 10 });
```

## Verdict
Adopt the two-field RAII pin whose destructor delegates to the manager's unpin policy; adapt assertion macros; nothing else is DuckDB-specific.
