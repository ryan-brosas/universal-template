<!-- capsule-v2 -->
# Vector Reinterpret — how do you re-view a vector's buffer as another type without breaking dictionary identity?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What does zero-copy reinterpretation require of type pairs, and what must survive when the source is a dictionary?

## Size-compat check under VERIFY_VECTORS; dict entries re-minted but id + global flag carried
**Path/Symbol:** `src/common/types/vector.cpp:CheckTypeIsReinterpretable` (:124-180), `Vector::Reinterpret` (:182-199).
**Signature:** `void Vector::Reinterpret(const Vector &other)`; guard active only when `DBConfigOptions::global_verification_mode == VERIFY_VECTORS`.
**Data Shape:** nested-vs-nested must match; flat types need equal byte size; STRUCT recurses over child pairs; LIST/ARRAY recurse into the single child.

### Decisive source
```cpp
if (GetVectorType() == VectorType::DICTIONARY_VECTOR && other_type != this_type) {
    Vector new_vector(this_type, nullptr);
    new_vector.Reinterpret(DictionaryVector::Child(other));   // reinterpret the DICT child
    auto &old_dict = buffer->Cast<DictionaryBuffer>();
    auto new_entry = make_shared_ptr<DictionaryEntry>(std::move(new_vector));
    // reinterpret re-mints the entry; the id and global flag are one contract and must survive together
    new_entry->id = old_dict.GetEntry().id;
    new_entry->global_dictionary = old_dict.GetEntry().global_dictionary;
    buffer = make_buffer<DictionaryBuffer>(old_dict.GetSelVector(), old_dict.Capacity(), std::move(new_entry));
}
```

**Flow:** optional debug validation → share the underlying buffer (ConstReference) → if the source is a dictionary whose entry type differs from the destination view, rebuild the entry from the reinterpreted child while copying the entry id and global-dictionary flag verbatim.
**Invariant:** dictionary cache identity (`id`, `global_dictionary`) is a cross-vector dedup contract — dropping it would silently fork caches that consumers assume are shared.
**Probe:** `grep -n 'new_entry->id = old_dict.GetEntry().id' src/common/types/vector.cpp` → :195; `grep -n 're-mints the entry' src/common/types/vector.cpp` → :194 comment.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "Reinterpret CheckTypeIsReinterpretable DictionaryEntry global_dictionary", limit: 10 });
```

## Verdict
Adopt verification-gated reinterpret plus identity-preserving dictionary re-minting; adapt to your vector variant union; omit the FSST/SHREDDED arms unless present in your engine.
