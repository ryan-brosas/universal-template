<!-- capsule-v2 -->
# Buffer manager virtual base — which methods must a custom BufferManager implement, and what do the defaults do?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What does porting a custom buffer manager require, and how do unimplemented capabilities fail?

## Default-implemented: HasTemporaryDirectory=false; NotImplemented: pool/pin/spill family
**Path/Symbol:** `src/storage/buffer_manager.cpp` (whole file, 142L) — `GetBufferPool` (:102), `GetTemporaryMemoryManager` (:106), `AddToEvictionQueue` (:110), temp-file trio (:126-141); per-context lookup via `ClientData::Get(context).client_buffer_manager` (:25-33).
**Signature:** `virtual BufferPool &GetBufferPool() const` throws Internal "This type of BufferManager does not have a buffer pool"; `bool HasTemporaryDirectory() const { return false; }`.
**Data Shape:** `GetAllocSize(size)` = `AlignValue<idx_t, Storage::SECTOR_SIZE>(size)` — the ONLY static helper implemented here.

### Decisive source
```cpp
BufferPool &BufferManager::GetBufferPool() const {
    throw InternalException("This type of BufferManager does not have a buffer pool");
}
bool BufferManager::HasTemporaryDirectory() const { return false; }   // safe default
unique_ptr<FileBuffer> BufferManager::ConstructManagedBuffer(...) {
    throw NotImplementedException("... can not construct managed buffers");
}
```

**Flow:** engine code asks for capabilities through the abstract interface; capability queries that are safe to answer negatively (temp dir presence, files-in-temp) return false; core machinery (pool, pins, spilling, small-memory registration) throws NotImplementedException/InternalException so misuse is loud.
**Invariant:** a custom manager MUST provide GetBufferPool/GetTemporaryMemoryManager/AddToEvictionQueue or every allocation path fails fast — there is no partial silent degradation.
**Probe:** `grep -c 'NotImplementedException' src/storage/buffer_manager.cpp` → `14`; `grep -n 'AlignValue<idx_t, Storage::SECTOR_SIZE>' src/storage/buffer_manager.cpp` → :40.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "BufferManager GetBufferPool GetAllocSize client_buffer_manager ConstructManagedBuffer", limit: 10 });
```

## Verdict
Adopt the capability-matrix shape (negative answers for queries, exceptions for machinery); adapt sector alignment to your device; omit prefetch stubs if you have no async IO layer.
