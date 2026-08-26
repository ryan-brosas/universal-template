<!-- capsule-v2 -->
# Vector layout zoo — what encodings must a vectorized operator tolerate, and which buffer type maps to which VectorType?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the full buffer-type × vector-type matrix and the nested-type child structure?

## The format contract operators sign up for
**Path/Symbol:** `src/include/duckdb/common/types/vector_buffer.hpp:VectorBufferType` (:30-40); `src/common/types/vector.cpp` (VectorTypeToString :370-393); child accessors `src/common/types/vector.cpp:RecursiveToUnifiedFormat` (:473-496); exercise table `src/function/table/system/test_vector_types.cpp`.
**Signature:** `enum class VectorBufferType : uint8_t { STANDARD_BUFFER, STRING_BUFFER, STRUCT_BUFFER, LIST_BUFFER, ARRAY_BUFFER, DICTIONARY_BUFFER, FSST_BUFFER, SHREDDED_BUFFER, SEQUENCE_BUFFER };`
**Data Shape:** VectorType ∈ {FLAT, FSST, SEQUENCE, DICTIONARY, CONSTANT, SHREDDED} (`GetVectorType()` reads from the buffer; null buffer ⇒ FLAT, vector.hpp:182-188). Buffer↔type mapping from the enum comments: STANDARD/STRING/STRUCT/LIST/ARRAY buffers serve FLAT **and** CONSTANT vectors; DICTIONARY_BUFFER serves DICTIONARY; FSST_BUFFER→FSST; SHREDDED_BUFFER→SHREDDED (Variant only); SEQUENCE_BUFFER→SEQUENCE (start+increment, no array).

### Decisive source
```cpp
// vector_buffer.hpp:30 — the mapping IS the documentation
enum class VectorBufferType : uint8_t {
	STANDARD_BUFFER,   // VectorType::FLAT/CONSTANT - Fixed-Size Type - Holds a single array of data
	STRING_BUFFER,     // VectorType::FLAT/CONSTANT - String          - string_t array + StringHeap
	STRUCT_BUFFER,     // VectorType::FLAT/CONSTANT - Struct          - struct child vectors
	LIST_BUFFER,       // VectorType::FLAT/CONSTANT - List            - list_entry_t array + child vector
	ARRAY_BUFFER,      // VectorType::FLAT/CONSTANT - Array           - array child vector
	DICTIONARY_BUFFER, // VectorType::DICTIONARY    - Any             - SelectionVector + dict child
	FSST_BUFFER,       // VectorType::FSST          - String          - string_t array + FSST table
	SHREDDED_BUFFER,   // VectorType::SHREDDED      - Variant         - shredded variant
	SEQUENCE_BUFFER    // VectorType::SEQUENCE      - Any             - linear sequence (start, increment)
};

// vector.cpp:473 — nested types expose children recursively; LIST/ARRAY one child, STRUCT a vector of them
if (input.GetType().InternalType() == PhysicalType::LIST) {
	RecursiveToUnifiedFormat(ListVector::GetChild(input), data.children.back());
} else if (... PhysicalType::ARRAY) {
	RecursiveToUnifiedFormat(ArrayVector::GetChild(input), data.children.back());
} else if (... PhysicalType::STRUCT) {
	for each entry: RecursiveToUnifiedFormat(children[i], data.children[i]);
}
```

**Flow:** Operators either handle every VectorType via ToUnifiedFormat, or call `Flatten()` at their boundary. STRING buffers own a string heap (strings are `string_t` pointers into it) — copying the buffer without the heap corrupts data; use AddHeapReference when aliasing. SEQUENCE vectors materialize on demand (`Sequence(start, increment, count)`). SHREDDED exists solely for Variant columns.
**Invariant:** An operator that assumes FLAT without flattening is incorrect BY CONSTRUCTION under debug verification (see debug-vector-verification capsule) — DuckDB's test harness deliberately injects dictionaries/constants/sequences into every result. Nested children have INDEPENDENT lengths (list child grows by append); never assume child size == parent count.
**Probe:** `bash -c "grep -c 'VectorType::' src/include/duckdb/common/types/vector_buffer.hpp"` → ≥ 9 (every enum line carries its VectorType annotation). Behavioral pin: `src/function/table/system/test_vector_types.cpp` builds FLAT/CONSTANT/DICTIONARY/SEQUENCE vectors across all types (struct comment :14).
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"ToUnifiedFormat UnifiedVectorFormat flatten","limit":8,"detail":"ids"}` resolves all per-buffer overrides incl. struct/array/list variants line-exact.

## Verdict
Adopt the buffer×type matrix and independent-child-length rules verbatim when designing a vector format set. Adapt the specific encodings (FSST/SHREDDED are DuckDB-specific) to your storage codecs. Omit Variant shredding unless you carry LogicalTypeId::VARIANT.
