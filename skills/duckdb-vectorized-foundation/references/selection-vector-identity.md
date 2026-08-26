<!-- capsule-v2 -->
# SelectionVector — how do you filter tuples without copying them, and when is a selection vector "unset"?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What are the ownership modes, the null-sentinel semantics, and the composition rule of `SelectionVector`?

## Tuple indirection primitive
**Path/Symbol:** `src/include/duckdb/common/types/selection_vector.hpp:SelectionVector` (:30-180); impl `src/common/types/selection_vector.cpp`.
**Signature:** `inline idx_t get_index(idx_t idx) const; inline void set_index(idx_t idx, idx_t loc); static SelectionVector Incremental(idx_t start, idx_t count); static idx_t Inverted(const SelectionVector &src, SelectionVector &dst, idx_t source_size, idx_t count); buffer_ptr<SelectionData> Slice(const SelectionVector &sel, idx_t count) const;`
**Data Shape:** `sel_vector : sel_t*` + shared `selection_data : buffer_ptr<SelectionData>` (owns heap) + `capacity`. THREE states: (1) **owning** — `Initialize(count)` allocates SelectionData (debug builds poison-fill with `sel_t max`, selection_vector.cpp:8-16); (2) **borrowing** — `Initialize(sel_t*, capacity)` points at foreign memory with `selection_data.reset()`; (3) **UNSET** — default/nullptr: `get_index(i)` returns `i` itself (`return sel_vector ? get_index_unsafe(idx) : idx;` hpp:136-138), i.e. identity mapping.

### Decisive source
```cpp
// hpp:136 — unset == identity; a null sel NEVER means "empty"
inline idx_t get_index(idx_t idx) const {
    return sel_vector ? get_index_unsafe(idx) : idx;
}

// cpp:44 — composing two sels: result[i] = target[new[i]] (dictionary-of-dictionary flattening)
buffer_ptr<SelectionData> SelectionVector::Slice(const SelectionVector &sel, idx_t count) const {
	auto data = make_buffer<SelectionData>(count);
	auto result_ptr = reinterpret_cast<sel_t *>(data->owned_data.get());
	for (idx_t i = 0; i < count; i++) {
		auto new_idx = sel.get_index(i);
		auto idx = this->get_index(new_idx);
		result_ptr[i] = UnsafeNumericCast<sel_t>(idx);
	}
	return data;
}
```

**Flow:** Operators thread one optional `const SelectionVector *sel` through every Execute/Select call. Filtering = building a new sel of survivors (never gathering data). Slicing an already-selected vector composes via `Slice` (new owned sel); `SliceInPlace` overwrites in place; `ShiftLeft(offset,count)` compacts after consuming a prefix.
**Invariant:** An UNSET sel is the full range [0,count) — code must treat nullptr and incremental identically (see `Vector::Slice`: `if (!sel.IsSet() && count == size()) return;` no-op). Indices stored are `sel_t` (uint32 by default): `set_index` funnels through `UnsafeNumericCast<sel_t>` — porting to 64-bit indices requires changing `sel_t`, not call sites. DEBUG builds verify bounds in `Verify(count, vector_size)` throwing InternalException on out-of-range.
**Probe:** `bash -c "grep -c 'get_index' src/include/duckdb/common/types/selection_vector.hpp"` → ≥ 3 (identity fallback + unsafe accessor + operator[] paths all present). Behavioral pin: `test/sql/conjunction/or_between.test` drives survivor-selection end-to-end.
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"SelectionVector Incremental Inverted get_index","limit":6,"detail":"ids"}` resolves `Incremental` hpp:74-76, `Inverted` hpp:77-90, `get_index` hpp:136-138 line-exact.

## Verdict
Adopt the three-state model, the identity-sel sentinel, and sel-composition arithmetic verbatim — any row-filtering engine needs exactly this. Adapt `sel_t` width and the allocator behind `AllocatedData` to your host. Omit the debug poison-fill and `-Warray-bounds` workaround comments (toolchain-specific).
