<!-- capsule-v2 -->
# Constant-vector NULL semantics — how is a constant NULL represented and how do nested nulls propagate?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What does SetNull do to the validity mask, buffer reuse, and STRUCT/ARRAY children?

## One row, one mask bit
**Path/Symbol:** `src/common/vector/constant_vector.cpp:ConstantVector::SetNull` (:37-87), `Reference(Vector&, const Value&, count_t)` (:32-35) via `CreateConstantBuffer` (:10-30), zero-sel (:89-98); consumer `src/execution/expression_executor/execute_function.cpp:216-222`.
**Signature:** `void SetNull(Vector &vector, count_t count); void SetNull(Vector &vector, bool is_null); const SelectionVector *ZeroSelectionVector(idx_t count, SelectionVector &owned_sel);`
**Data Shape:** A CONSTANT vector stores exactly one element at index 0; its null state is `validity.RowIsValid(0)`. Buffer types eligible for in-place nulling: STANDARD/STRUCT/ARRAY/LIST/STRING (anything else → replace with fresh NullValue buffer).

### Decisive source
```cpp
// :37 — try to keep the buffer; only non-reusable buffer classes get replaced
if (needs_new_buffer) {
	// we cannot re-use the buffer - refer a null-value ...
	Reference(vector, Value(vector.GetType()), count);
	return;
}
vector.SetVectorType(VectorType::CONSTANT_VECTOR);
FlatVector::SetSize(vector, count);
SetNull(vector, true);

// :58 — nulling a CONSTANT = clearing bit 0 of the validity mask
auto &validity = vector.BufferMutable().GetValidityMask();
validity.Set(0, !is_null);
if (is_null && internal_type == PhysicalType::STRUCT) {
	// set all child entries to null as well
	auto &entries = StructVector::GetEntries(vector);
	for (auto &entry : entries) {
		entry.SetVectorType(VectorType::CONSTANT_VECTOR);
		ConstantVector::SetNull(entry, is_null);      // recurse into children
	}
} else if (is_null && internal_type == PhysicalType::ARRAY) {
	// ARRAY child stays flat: null EVERY slot of the single row's array
	for (idx_t i = 0; i < array_size; i++) FlatVector::SetNull(child, i, is_null);
}
```

**Flow:** Setting a constant NULL reuses the existing buffer when its class permits (cheap: flip one validity bit + stamp size), else references an all-null Value. STRUCT nulls cascade to every child (each child becomes a constant NULL itself — children are independent vectors). ARRAY nulls flip each element of row 0 in the shared child. Consumers detect it with `ConstantVector::IsNull(v)`; scalar execution short-circuits on any NULL constant argument under DEFAULT_NULL_HANDLING.
**Invariant:** A constant STRUCT null is represented in BOTH parent mask AND child masks — readers may check either level, writers must maintain both. The logical size (`count`) of the constant vector is set independently of storage (1 element): never infer "how many rows" from buffer capacity. `ZeroSelectionVector(count, owned_sel)` returns the SHARED static zero-sel for counts ≤ STANDARD_VECTOR_SIZE and materializes an owned one above — porters must not free the returned pointer.
**Probe:** `bash -c "grep -c 'needs_new_buffer' src/common/vector/constant_vector.cpp"` → ≥ 3 (declare+compute+use; executed count is exactly 4). Behavioral pin: `test/api/test_scalar_function_decimal_return.cpp:13` executes `ConstantVector::SetNull(result, true)` directly.
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"ConstantVector SetNull struct child entries","limit":5,"detail":"ids"}` resolves `ConstantVector.SetNull` :58-87 line-exact.

## Verdict
Adopt mask-bit null representation, buffer-class-gated reuse, and STRUCT/ARRAY cascade rules verbatim. Adapt the ValidityMask internals (bit-packing layout is host-tunable). Omit the deprecated `Flatten(idx_t count)` shims around this plane (marked `[[deprecated]]`, vector.hpp:111-117).
