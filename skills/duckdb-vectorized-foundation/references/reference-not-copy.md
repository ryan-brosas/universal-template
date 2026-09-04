<!-- capsule-v2 -->
# Vector reference-vs-copy discipline — when does an operation alias buffers and when must it copy?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** Which Vector operations are zero-copy aliases, and what is the one API that can change a vector's logical data?

## Zero-copy buffer algebra
**Path/Symbol:** `src/common/types/vector.cpp:Vector::Reference` (:110-117), `ReferenceAndSetType` (:119-121), `ConstReference` (:201-203), `Slice` (:209-248), `Dictionary` (:250-271); class contract `src/include/duckdb/common/types/vector.hpp:35-241`.
**Signature:** `void Reference(const Vector &other); void ReferenceAndSetType(const Vector &other); void Slice(const Vector &other, const SelectionVector &sel, idx_t count); void Slice(const SelectionVector &sel, idx_t count); void Dictionary(buffer_ptr<DictionaryEntry> reusable_dict, const SelectionVector &sel, idx_t sel_count);`
**Data Shape:** A Vector = `{LogicalType type; mutable buffer_ptr<VectorBuffer> buffer;}` (hpp:237-240). Copy ctor is DELETED (`Vector(const Vector&) = delete`, hpp:53) — vectors move or reference, never silently deep-copy. The vector type lives IN the buffer (`GetVectorType()` reads `buffer_ref->GetVectorType()`), so a null buffer means FLAT_VECTOR.

### Decisive source
```cpp
// :110 — Reference: type-checked ALIAS, no bytes moved
void Vector::Reference(const Vector &other) {
	if (other.GetType().id() != GetType().id()) {
		throw InternalException("Vector::Reference used on vector of different type (source %s referenced %s)", ...);
	}
	ConstReference(other);              // AssignSharedPointer(buffer, other.buffer)
}
void Vector::ReferenceAndSetType(const Vector &other) {
	type = other.GetType();             // escape hatch: adopt the type too
	ConstReference(other);
}

// :221 — Slice: turn into a dictionary over the SAME buffer (zero-copy)
void Vector::Slice(const SelectionVector &sel, idx_t count) {
	if (!sel.IsSet() && count == size()) {
		return; // no-op: identity sel over full length
	}
	auto new_buffer = buffer->Slice(GetType(), sel, count); // dictionary/merged slice per buffer type
	if (new_buffer) buffer = std::move(new_buffer);
	FlatVector::SetSize(*this, count_t(count));
}

// hpp:113-116 — the ONLY logical-mutation primitive is deliberately marked:
//! Flatten the vector ... While Flatten mutates the buffers / vector type,
//! it does not change the *logical* representation of a vector
DUCKDB_API void Flatten() const;        // note: const!
```

**Flow:** Producers write into fresh/cached flat vectors; everything downstream passes vectors by reference. Re-targeting a result column = `Reference` (alias). Restricting to survivors = `Slice` (alias + selection). Sharing a compressed child across chunks = `Dictionary(entry, sel, n)`. Only `Flatten()` (and writes through `FlatVector::GetDataMutable`) change bytes, and Flatten preserves logical content by definition.
**Invariant:** After `Reference`, both vectors observe each other's future mutations — code that keeps a "snapshot" via Reference has a use-after-free/mutation bug; own a copy via `VectorOperations::Copy` instead. `Slice(sel,count)` with identity sel and equal size MUST be a no-op (buffer sharing survives). STRUCT cannot be dictionary-encoded (`throw InternalException("Struct vectors cannot be dictionaries")`, :266-268).
**Probe:** `bash -c "grep -c 'Vector(const Vector &other) = delete' src/include/duckdb/common/types/vector.hpp"` → ≥ 1 pins no-silent-copy at the pin. Behavioral pin: `test/api/test_scalar_function_decimal_return.cpp` exercises result-vector reuse semantics around SetNull.
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"Vector Slice dictionary buffer flatten","limit":6,"detail":"ids"}` resolves the whole slice/flatten plane line-exact (`VectorBuffer.Slice` vector_buffer.cpp:193-205, `DictionaryBuffer.FlattenSliceInternal` dictionary_vector.cpp:146-164).

## Verdict
Adopt the alias/slice/dictionary triad and the deleted-copy-contract verbatim — this is what makes columnar operators allocation-light. Adapt the shared_ptr buffer ownership to your language's refcounting/Rc. Omit DuckDB's `VectorCache` integration details if your host lacks per-thread allocator caches (see data-chunk-reset capsule for the cache contract).
