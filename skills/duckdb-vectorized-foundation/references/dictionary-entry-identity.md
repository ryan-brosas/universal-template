<!-- capsule-v2 -->
# Dictionary identity & Reinterpret — how do dictionary entries stay identifiable across re-encoding so caches and reuse survive?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the DictionaryEntry identity contract, and what must a type-reinterpreting operation preserve?

## Identity travels with the entry
**Path/Symbol:** `src/include/duckdb/common/vector/dictionary_vector.hpp:DictionaryEntry` (:14-32); `src/common/types/vector.cpp:Vector::Reinterpret` (:182-199); factories `src/common/vector/dictionary_vector.cpp:CreateReusableDictionary/Global` (:166-178); verify `DictionaryBuffer::VerifyInternal` (:47-64).
**Signature:** `void Vector::Reinterpret(const Vector &other);` `static buffer_ptr<DictionaryEntry> CreateReusableDictionary(const LogicalType &type, const idx_t &size);`
**Data Shape:** DictionaryEntry = `{Vector data; string id; bool global_dictionary=false; mutable mutex cached_hashes_lock; mutable unique_ptr<Vector> cached_hashes;}` — id uniquely identifies re-occurring dictionaries; global_dictionary marks producer-lifetime stable entries (set only via CreateReusableGlobalDictionary).

### Decisive source
```cpp
// vector.cpp:189 — reinterpreting a dictionary must RE-MINT the entry but keep identity
if (GetVectorType() == VectorType::DICTIONARY_VECTOR && other_type != this_type) {
	Vector new_vector(this_type, nullptr);
	new_vector.Reinterpret(DictionaryVector::Child(other));
	auto &old_dict = buffer->Cast<DictionaryBuffer>();
	auto new_entry = make_shared_ptr<DictionaryEntry>(std::move(new_vector));
	// reinterpret re-mints the entry; the id and global flag are one contract and must survive together
	new_entry->id = old_dict.GetEntry().id;
	new_entry->global_dictionary = old_dict.GetEntry().global_dictionary;
	buffer = make_buffer<DictionaryBuffer>(old_dict.GetSelVector(), old_dict.Capacity(), std::move(new_entry));
}

// dictionary_vector.cpp:166 — fresh reusable entries get UUID ids
entry->id = UUID::ToString(UUID::GenerateRandomUUID());
```

**Flow:** When bytes of a differently-typed view are needed over the same dictionary (e.g. re-reading an encoded column as another physical layout), the child is reinterpreted into a NEW entry, while id + global flag carry over untouched and the SAME selection vector wraps it. Downstream, `TryExecuteDictionaryExpression` keys its output cache on this id; hash caching (`GetCachedHashes`, :180+) locks per-entry.
**Invariant:** id and global_dictionary form ONE contract — copying either alone desynchronizes cache validity vs. stability guarantees (the upstream comment says exactly this). The sel vector of the reinterpret result is preserved byte-for-byte from the old dictionary. Verification (`VerifyInternal`) requires the WHOLE child be valid because consumers may read any entry in [0, dict size), not only selected ones ("e.g. ColumnDataCollection copies the whole dictionary to keep it compressed").
**Probe:** `bash -c "grep -c 'global_dictionary' src/common/vector/dictionary_vector.cpp"` → ≥ 1 (actual 1: the CreateReusableGlobalDictionary flag-setter — consumers live in headers); identity serializer-side handling pinned by `bash -c "grep -c 'DictionaryVector::DictionarySize' src/common/types/vector.cpp"` → ≥ 1 (actual 2: vector.cpp:526-530 preserves dictionary+size across serialization round-trips).
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"TryExecuteDictionaryExpression dictionary optimization reusable","limit":6,"detail":"ids"}` resolves both factories dictionary_vector.cpp:166-178 line-exact.

## Verdict
Adopt entry-identity (id + global flag) preservation through re-encoding verbatim whenever your engine caches derived artifacts per dictionary. Adapt UUID generation and mutex/hash-cache plumbing to host primitives. Omit FSST-string-specific reinterpret checks (`CheckTypeIsReinterpretable` under VERIFY_VECTORS debug mode).
