<!-- capsule-v2 -->
# VectorCache + DataChunk.Reset — how does per-thread execution reuse buffers across millions of chunks without allocating?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What exactly happens on chunk Reset, and why must types be COPIED at Initialize time?

## Allocation-free steady state
**Path/Symbol:** `src/common/types/data_chunk.cpp:DataChunk::Initialize(Allocator&, ...)` (:53-75), `Reset` (:107-119), `SetChildCardinality` (:155-171), `DeriveSize` (:77-89); cache `src/common/types/vector_cache.cpp:VectorCache::ResetFromCache` (:127-132) / `VectorCacheEntry::ResetFromCache` (:51-92); state plumbing `src/execution/expression_executor_state.hpp:ExpressionState` (intermediate_chunk).
**Signature:** `void Initialize(Allocator &allocator, const vector<LogicalType> &types, const vector<bool> &initialize, idx_t capacity); void Reset(); void SetChildCardinality(idx_t count_p);`
**Data Shape:** DataChunk = `vector<Vector> data` + PARALLEL `vector<VectorCache> vector_caches` + `optional_idx count`. `initialize[i]=false` columns get null-buffer placeholder vectors and an EMPTY cache slot — the two vectors stay index-aligned by construction.

### Decisive source
```cpp
// :58 — WHY copy types: atomic refcount contention on shared ExtraTypeInfo
for (idx_t i = 0; i < types.size(); i++) {
	// We copy the type here so we don't create another reference to the same shared_ptr<ExtraTypeInfo>
	// Otherwise, threads will constantly increment/decrement the atomic ref count to the same shared_ptr
	// This is necessary to avoid heavy contention on the atomic on many-core machines
	auto copied_type = types[i].Copy();
	...
	VectorCache cache(allocator, copied_type, capacity);
	data.emplace_back(cache);            // vector starts as reset-from-cache flat vector
	vector_caches.push_back(std::move(cache));
}

// :107 — Reset = rewind EVERY column to its cache-owned buffer (no malloc)
void DataChunk::Reset() {
	count = optional_idx();
	if (data.empty() || vector_caches.empty()) { count = 0; return; }
	if (vector_caches.size() != data.size()) {
		throw InternalException("VectorCache and column count mismatch in DataChunk::Reset");
	}
	for (idx_t i = 0; i < ColumnCount(); i++) data[i].ResetFromCache(vector_caches[i]);
}

// :155 — cardinality is a property stamped on every flat/constant column
if (!v.GetBufferRef()) continue;                       // placeholders skipped
auto vtype = v.GetVectorType();
if (vtype == FLAT_VECTOR || vtype == CONSTANT_VECTOR) FlatVector::SetSize(v, count_p);
else if (v.size() != count_p) throw InternalException(...); // dictionary etc. cannot resize
```

**Flow:** Executor states own one `intermediate_chunk` initialized from their children's types; every Execute call begins with `state->intermediate_chunk.Reset()` which re-points each column at its cached buffer (flat, fresh validity). Results are written in place; cardinality is set once at the end via `SetChildCardinality`.
**Invariant:** After Reset, all columns are FLAT with full-capacity buffers and stale bytes are logically invisible (size is unset until cardinality is stamped). Columns created with `initialize=false` must NEVER be Reset into usable storage — they are reference targets only. A size mismatch between caches and columns is a hard InternalException (alignment contract). ExpressionExecutor::Execute's DEBUG assertion (`FlatVector::ValidityMutable(result).CheckAllValid(count)`, expression_executor.cpp:255-266) enforces that result vectors were reset or never used — reusing a dirty result would leak stale validity bits.
**Probe:** `bash -c "grep -c 'vector_caches' src/common/types/data_chunk.cpp"` → ≥ 6 (Initialize×2, Reset×3, Destroy, Move). Behavioral pin: whole sqllogictest suite depends on it; deterministic pin `bash -c "grep -c 'intermediate_chunk.Reset' src/execution/expression_executor/execute_case.cpp"` → ≥ 1.
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"ResetFromCache VectorCache","limit":5,"detail":"ids"}` resolves `VectorCache.ResetFromCache` vector_cache.cpp:127-132 and entry-level :51-92 line-exact.

## Verdict
Adopt the parallel cache-slot design, type-copy rationale (many-core refcount storm), and reset-to-cache protocol verbatim for any hot loop over batches. Adapt capacity policy (DuckDB pins STANDARD_VECTOR_SIZE=2048 defaults; your width may differ) and allocator injection. Omit `VectorAppendMode::ALLOW_RESIZE` growth paths if your chunks are fixed-width.
