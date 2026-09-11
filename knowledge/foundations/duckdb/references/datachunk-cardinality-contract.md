<!-- capsule-v2 -->
# DataChunk cardinality contract — who owns a chunk's row count, and when is it "unset"?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How do `optional_idx` count semantics plus `DeriveSize`/`SetChildCardinality` prevent column-count drift?

## count is optional; derive from first buffer-backed vector; child resize restricted to flat/constant
**Path/Symbol:** `src/common/types/data_chunk.cpp` — `DeriveSize` (:77-89), `Reset` (:107-119), `CheckCardinality` (:145-153), `SetChildCardinality` (:155-171), `Append` (:254-286).
**Signature:** `idx_t DeriveSize() const`; `void SetChildCardinality(idx_t count_p)`; `count` is an `optional_idx` — unset means "derive from children".
**Data Shape:** null-buffer placeholders (`InitializeEmpty`) carry no data and are skipped by both derivation and resize.

### Decisive source
```cpp
idx_t DataChunk::DeriveSize() const {
    for (const auto &v : data) {
        if (v.GetBufferRef()) return v.size();     // first real column decides
    }
    if (data.empty())
        return 0;   // "a column-less chunk has nothing to derive a cardinality from"
    throw InternalException("DataChunk::size() called but neither count was set, ...");
}
void DataChunk::SetChildCardinality(idx_t count_p) {
    for (auto &v : data) {
        if (!v.GetBufferRef()) continue;
        auto vtype = v.GetVectorType();
        if (vtype == FLAT_VECTOR || vtype == CONSTANT_VECTOR) FlatVector::SetSize(v, count_p);
        else if (v.size() != count_p) throw InternalException("... cannot change vector size ...");
    }
    this->count = count_p;
}
```

**Flow:** operations that know the row count set it explicitly (or leave it unset after Copy so it re-derives); Append verifies every child matches the chunk's current size BEFORE appending, then `CheckCardinality(current+sel_count)` re-validates; Reset restores each vector from its VectorCache.
**Invariant:** non-flat/non-constant vectors (dictionary etc.) must ALREADY have the target size — SetChildCardinality throws rather than materializing them; a mismatch between any child size and chunk size is an InternalException, never silent truncation.
**Probe:** `grep -c 'count = optional_idx()' src/common/types/data_chunk.cpp` → `6`; `grep -n 'cannot change vector size because it is not a flat or constant vector' src/common/types/data_chunk.cpp` → :166.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "DataChunk DeriveSize SetChildCardinality CheckCardinality Append", limit: 10 });
```

## Verdict
Adopt optional-count-with-derived-fallback as the chunk cardinality discipline; adapt your vector-type enum; omit serialization verification branches (VERIFY_SERIALIZATION) unless you port debug modes too.
