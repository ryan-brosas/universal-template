<!-- capsule-v2 -->
# Vector serialize round-trip — how do compressed vector types (dict/constant/sequence) survive serialization?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the on-the-wire contract for dictionary/constant/sequence vectors, including the dict-pruning size gate?

## vector_type property + per-type payload; dictionary only when used*2 < count
**Path/Symbol:** `src/common/types/vector.cpp:Vector::Serialize` (:514-722) and `Vector::Deserialize` (:732-880); property ids 90-92 (type+payload), 100-102 (validity/data).
**Signature:** `void Vector::Serialize(Serializer&, bool compressed_serialization)`; compression is silently disabled when targeting versions older than `StorageVersion::V1_3_0` (:521-523).
**Data Shape:** dictionary path writes `sel_vector` (count × sel_t) + pruned `dict_count`; sequence writes only `(seq_start, seq_increment)`; constant resizes to 1, serializes one value, then restores.

### Decisive source
```cpp
if (vtype == VectorType::DICTIONARY_VECTOR && DictionarySize(*this).IsValid()) {
    // dictionaries may be row-group sized — restrict to the used subset and remap
    sel_t CODE_UNSEEN = static_cast<sel_t>(dict_count);
    ... map_sel[pos]==CODE_UNSEEN → assign next used slot ...
    if (used_count * 2 < count) {          // only serialize as dict if actually smaller
        serializer.WriteProperty(90, "vector_type", DICTIONARY_VECTOR);
        serializer.WriteProperty(91, "sel_vector", ...);
        serializer.WriteProperty(92, "dict_count", used_count);
        return dict.Serialize(serializer, false);
    }
}
```

**Flow:** dispatch on vector type → constant/sequence/dict take compact paths (early return) → fallback flattens through ToUnifiedFormat and writes validity mask + data per physical type; deserialize mirrors each branch (`ReadPropertyWithExplicitDefault<Flat>` for old files) and rebuilds the same vector class.
**Invariant:** the CODE_UNSEEN sentinel equals `dict_count` so unmapped dictionary entries are provably never referenced; a dictionary that fails the 2× size test must degrade to flat serialization — the reader accepts both shapes for any version ≥ V1_3_0.
**Probe:** `grep -n 'used_count \* 2 < count' src/common/types/vector.cpp` → :548; `grep -n 'CODE_UNSEEN' src/common/types/vector.cpp | head -1` → :535.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "Vector Serialize Deserialize DICTIONARY_VECTOR CODE_UNSEEN seq_increment", limit: 10 });
```

## Verdict
Adopt version-gated compressed payloads with explicit degradation rules; adapt property-id numbering to your framing; omit GEOMETRY legacy branches if you have no spatial types.
