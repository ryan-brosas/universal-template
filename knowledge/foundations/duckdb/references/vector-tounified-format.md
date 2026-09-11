<!-- capsule-v2 -->
# ToUnifiedFormat — what is the one read protocol every operator uses on any vector?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How do consumers access flat/constant/dictionary/FSST/sequence vectors uniformly, and which types force flattening?

## Vector-level dispatch; only FLAT/CONSTANT/DICTIONARY served natively — others flatten
**Path/Symbol:** `src/common/types/vector.cpp:Vector::ToUnifiedFormat` (:458-467); recursive variant `RecursiveToUnifiedFormat` (:473-496) walking LIST child / ARRAY child / STRUCT entries.
**Signature:** `void Vector::ToUnifiedFormat(UnifiedVectorFormat &format) const` (count-less; the `(idx_t count, ...)` overloads are deprecated shims :454-456); fills `{sel, data, validity, owned_sel, physical_type}`.
**Data Shape:** `format.physical_type = GetType().InternalType()` set FIRST so callers can typed-view `data`; SelCache (`merge_cache`) dedupes selection buffers across columns when slicing.

### Decisive source
```cpp
void Vector::ToUnifiedFormat(UnifiedVectorFormat &format) const {
    format.physical_type = GetType().InternalType();
    auto vtype = GetVectorType();
    if (vtype != FLAT_VECTOR && vtype != CONSTANT_VECTOR && vtype != DICTIONARY_VECTOR) {
        // FSST/SEQUENCE/SHREDDED: flatten first so the buffer can provide unified format
        Flatten();
    }
    Buffer().ToUnifiedFormat(format);
}
```

**Flow:** caller declares a stack `UnifiedVectorFormat` → per column call → for exotic vector kinds the buffer is flattened in place (mutating! hence the FIXME "should ideally be const") → read rows via `sel->get_index(i)` + validity mask.
**Invariant:** after ToUnifiedFormat the data pointer is stable only for the duration of the call chain that owns the buffer — flattening may reallocate; nested children must be pulled through RecursiveUnifiedVectorFormat, not guessed from the parent.
**Probe:** `grep -n 'FSST/SEQUENCE/SHREDDED: flatten first' src/common/types/vector.cpp` → :463; `grep -c 'RecursiveToUnifiedFormat' src/common/types/vector.cpp` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "ToUnifiedFormat UnifiedVectorFormat RecursiveUnifiedVectorFormat Flatten", limit: 10 });
```

## Verdict
Adopt the single normalized-read struct with explicit flatten-on-demand for exotic layouts; adapt to your vector union; document the mutation-in-const-method tradeoff your port makes.
