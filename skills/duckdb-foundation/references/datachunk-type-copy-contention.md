<!-- capsule-v2 -->
# DataChunk zero-atomic type copy — why does Initialize copy LogicalTypes instead of referencing them?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What many-core contention hazard does the VectorCache-per-column initialization avoid?

## Copy types at Initialize; per-vector caches give Reset O(cols) restore
**Path/Symbol:** `src/common/types/data_chunk.cpp:Initialize(Allocator&, types, initialize, capacity)` (:53-75); `Reset` (:107-119); `vector_caches` moved in Split/Fuse (:215-240).
**Signature:** `void Initialize(Allocator &allocator, const vector<LogicalType> &types, const vector<bool> &initialize, idx_t capacity)`; each column gets `VectorCache cache(allocator, copied_type, capacity)`.
**Data Shape:** two parallel vectors: `data` (working Vectors) + `vector_caches` (owned backing buffers); mismatch throws `"VectorCache and column count mismatch in DataChunk::Reset"`.

### Decisive source
```cpp
for (idx_t i = 0; i < types.size(); i++) {
    // We copy the type here so we don't create another reference to the same
    // shared_ptr<ExtraTypeInfo>. Otherwise, threads will constantly increment/decrement
    // the atomic ref count to the same shared_ptr — heavy contention on many-core machines.
    // (Nested types still contend one level down: this is a shallow copy, depth=1.)
    auto copied_type = types[i].Copy();
    ...
    VectorCache cache(allocator, copied_type, capacity);
    data.emplace_back(cache);
    vector_caches.push_back(std::move(cache));
}
```

**Flow:** Initialize builds cache+vector pairs → operator loop mutates `data` → Reset calls `data[i].ResetFromCache(vector_caches[i])`, restoring capacity and clearing payloads without reallocation → Split/Fuse MOVE both planes together so caches stay aligned.
**Invariant:** `data[i]` must always be paired with `vector_caches[i]` of identical type; any transform that moves columns must move BOTH arrays or Reset corrupts memory.
**Probe:** `grep -n 'auto copied_type = types\[i\].Copy()' src/common/types/data_chunk.cpp` → :64; `grep -c 'vector_caches' src/common/types/data_chunk.cpp` → counts 12 occurrences across reset/split/fuse paths (`grep -c 'vector_caches' = 12`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "DataChunk Initialize VectorCache ResetFromCache vector_caches", limit: 10 });
```

## Verdict
Adopt copy-on-initialize to dodge shared_ptr atomic contention plus paired-cache reset semantics; adapt your type identity model; omit the depth-1 nested caveat only if your types are flat.
