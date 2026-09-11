<!-- capsule-v2 -->
# Orrify (ToUnifiedFormat) — how do you read ANY DuckDB vector (flat, constant, or dictionary) without materializing it?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the canonical element-access protocol for a `Vector`, and what does the converter do per vector type?

## Canonical unified read format (Orrify)
**Path/Symbol:** `src/common/types/vector.cpp:Vector::ToUnifiedFormat` (:458-467); `src/common/vector/flat_vector.cpp:StandardVectorBuffer::ToUnifiedFormat` (:215-223); `src/common/vector/dictionary_vector.cpp:DictionaryBuffer::ToUnifiedFormat` (:65-76); base throwing impl `src/common/types/vector_buffer.cpp:144-146`.
**Signature:** `void Vector::ToUnifiedFormat(UnifiedVectorFormat &format) const` — note: NO count parameter (the `(idx_t count, ...)` overloads are `[[deprecated]]`, vector.hpp:104-133; port to the count-less form).
**Data Shape:** `UnifiedVectorFormat` (unified_vector_format.hpp:22-67) = `{ const SelectionVector *sel; const_data_ptr_t data; ValidityMask validity; SelectionVector owned_sel; PhysicalType physical_type; }` — copy/move-only, no default copies; typed access via `format.GetData<T>()` (asserts physical type outside `DUCKDB_DEBUG_NO_SAFETY`). Nested types recurse via `RecursiveUnifiedVectorFormat {unified, children[], logical_type}` (vector.cpp:473-496 walks LIST child / ARRAY child / STRUCT entries).

### Decisive source
```cpp
// vector.cpp:458 — dispatch happens at the VECTOR level...
void Vector::ToUnifiedFormat(UnifiedVectorFormat &format) const {
	format.physical_type = GetType().InternalType();
	auto vtype = GetVectorType();
	if (vtype != VectorType::FLAT_VECTOR && vtype != VectorType::CONSTANT_VECTOR &&
	    vtype != VectorType::DICTIONARY_VECTOR) {
		// FSST/SEQUENCE/SHREDDED: flatten first so the buffer can provide unified format
		Flatten();
	}
	Buffer().ToUnifiedFormat(format);
}

// flat_vector.cpp:215 — ...and free conversion lives in the BUFFER
void StandardVectorBuffer::ToUnifiedFormat(UnifiedVectorFormat &format) const {
	if (vector_type == VectorType::CONSTANT_VECTOR) {
		format.sel = ConstantVector::ZeroSelectionVector(Size(), format.owned_sel);
	} else {
		format.sel = FlatVector::IncrementalSelectionVector();
	}
	format.data = data_ptr;
	format.validity = validity;
}

// dictionary_vector.cpp:65 — dictionary: own the sel, point INTO the (flattened) child
void DictionaryBuffer::ToUnifiedFormat(UnifiedVectorFormat &format) const {
	format.owned_sel.Initialize(sel_vector);
	format.sel = &format.owned_sel;
	auto &child = entry->data;
	if (child.GetVectorType() != VectorType::FLAT_VECTOR) {
		entry->data.Flatten();   // in-place, once, inside the shared entry
	}
	format.data = FlatVector::GetData(entry->data);
	format.validity = FlatVector::ValidityMutable(entry->data);
}
```

**Flow:** (1) record physical type; (2) FLAT → borrow process-wide incremental sel; CONSTANT → all-zero sel (shared static when `Size() <= STANDARD_VECTOR_SIZE`, owned fallback otherwise, constant_vector.cpp:89-98); DICTIONARY → copy sel into `format.owned_sel`, flatten the SHARED child entry in place if needed, point data/validity into the child; anything exotic (FSST/SEQUENCE/SHREDDED) → `Flatten()` first because those buffers throw `"ToUnifiedFormat not supported for this buffer type - flatten first"`.
**Invariant:** Element *i* is ALWAYS `data[sel->get_index(i)]` with validity `validity.RowIsValid(sel->get_index(i))` — never index `data` directly. Flat/constant/dictionary convert with ZERO data copying ("for free"); the dictionary child flattening mutates shared state (idempotent, monotone: flat stays flat). `RecursiveToUnifiedFormat` mirrors the same recursion a porter needs for LIST/ARRAY/STRUCT children.
**Probe:** `bash -c "grep -c 'ToUnifiedFormat' test/api/test_aggregate_state_bind_data.cpp"` → ≥ 1 (actual 4 at the pin: API-level consumers reading result vectors through the unified format); behavioral pin: any sqllogictest run exercises it end-to-end, e.g. `bash -c 'grep -c "query" test/sql/conjunction/or_between.test'` ≥ 2.
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"ToUnifiedFormat","limit":8,"detail":"ids"}` resolves all seven buffer overrides line-exact (`Vector.ToUnifiedFormat` :458-467, `StandardVectorBuffer` :215-223, `DictionaryBuffer` :65-76, struct/array/list variants).

## Verdict
Adopt the unified-format read protocol and the three-way free-conversion invariant verbatim — it is the single most reused contract in the engine. Adapt the exotic-format flatten-first list (FSST/SEQUENCE/SHREDDED are DuckDB-specific layouts) and the deprecated count-arg shim layer. Omit the `UnifiedVariantVector` accessor family (variant-specific shredding metadata, unified_vector_format.hpp:75-94). Caveat: header `unified_vector_format.hpp` is parse_partial at isolated declaration lines (coverage generation 2026-08-23T11:00:58Z, head==base) — declarations were read directly from source; no behavioral claim rests on the flagged lines.
