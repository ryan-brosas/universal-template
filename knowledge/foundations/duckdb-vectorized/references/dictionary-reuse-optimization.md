<!-- capsule-v2 -->
# Dictionary-expression reuse — how do you evaluate a scalar function once per DICTIONARY VALUE instead of once per row?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** Under which eligibility gates is a function computed over the dictionary child and re-emitted as a new dictionary?

## Compute the unique values, alias them for every row
**Path/Symbol:** `src/execution/expression_executor/execute_function.cpp:ExecuteFunctionState::TryExecuteDictionaryExpression` (:49-122); eligibility ctor (:9-44); reusable entry factory `src/common/vector/dictionary_vector.cpp:DictionaryVector::CreateReusableDictionary` (:166-171); identity `DictionaryEntry` (`src/include/duckdb/common/vector/dictionary_vector.hpp:14-32`).
**Signature:** `bool TryExecuteDictionaryExpression(const BoundFunctionExpression &expr, DataChunk &args, ExpressionState &state, Vector &result);`
**Data Shape:** Constants: `MAX_DICTIONARY_SIZE_THRESHOLD = 20000`, `CHUNK_FILL_RATIO_THRESHOLD = 0.5`. Cache in state: `output_dictionary : buffer_ptr<DictionaryEntry>` + `current_input_dictionary_id : string`. A storage-origin dictionary carries `DictionarySize` (optional_idx) and non-empty `DictionaryId`.

### Decisive source
```cpp
// :12 — eligibility decided ONCE at state init
if (!expr.IsConsistent() || expr.IsVolatile() || expr.CanThrow()) {
	return;                 // Needs to be consistent, non-volatile, and non-throwing
}
// + exactly one non-constant, non-STRUCT child => input_col_idx valid

// :71 — runtime gates
if (input_dictionary_size >= MAX_DICTIONARY_SIZE_THRESHOLD) return false;   // too big
const auto chunk_fill_ratio = static_cast<double>(args.size()) / STANDARD_VECTOR_SIZE;
if (input_dictionary_size > STANDARD_VECTOR_SIZE && chunk_fill_ratio <= CHUNK_FILL_RATIO_THRESHOLD) {
	// dict larger than one chunk: only worth it if chunk >50% full —
	// "This protects the optimization against selective filters"
	return false;
}
// :100 — run the function over the WHOLE dictionary in chunk-sized slices
for (idx_t offset = 0; offset < input_dictionary_size; offset += STANDARD_VECTOR_SIZE) {
	const auto count = MinValue<idx_t>(input_dictionary_size - offset, STANDARD_VECTOR_SIZE);
	Vector offset_input(DictionaryVector::Child(unary_input), offset, offset + count);
	input_chunk.data[input_col_idx.GetIndex()].Reference(offset_input);
	input_chunk.SetChildCardinality(count);
	expr.Function().Execute(input_chunk, state, output_intermediate);
	VectorOperations::Copy(output_intermediate, new_dictionary->data, count, 0, offset);
}
// :119 — result becomes a dictionary with THE SAME selection vector as the input
result.Dictionary(output_dictionary, DictionaryVector::SelVector(unary_input), args.size());
```

**Flow:** Gate on consistency/volatility/throwing + single non-constant input → require a storage dictionary (valid size + id) → size/fill-ratio gates → if this exact dictionary id wasn't cached in this state, compute f(child) slice-wise into a fresh reusable entry → publish result as `dictionary(new_entry, input_sel)` so row i shows f(value[sel[i]]) with ZERO per-row work. Publish happens only after full computation, so a mid-flight throw cannot leave a half-initialized cache (:85-87 comment).
**Invariant:** The output dictionary's row mapping equals the INPUT's sel — never reslice by output cardinality. Cache keying is by dictionary ID STRING, not pointer; stale ids must invalidate (`current_input_dictionary_id != input_dictionary_id` recomputes). `ResetDictionaryStates()` (:124-132) clears the cache recursively when the executor's inputs change.
**Probe:** `bash -c "grep -oE 'MAX_DICTIONARY_SIZE_THRESHOLD|CHUNK_FILL_RATIO_THRESHOLD' src/execution/expression_executor/execute_function.cpp | wc -l"` → ≥ 4 (each constant declared once + used once per gate; executed count is exactly 4 at the pin). Behavioral pin: `test/sql/storage/null_byte_storage.test` exercises dictionary-encoded scans end-to-end.
**Retrieve:** `search_graph {"project":"ext-duckdb","query":"TryExecuteDictionaryExpression dictionary optimization reusable","limit":6,"detail":"ids"}` resolves the method execute_function.cpp:49-122 plus both factories line-exact.

## Verdict
Adopt the gate ladder and the same-sel dictionary re-emission verbatim — it converts O(rows) string/numeric function calls into O(distinct). Adapt the thresholds to your vector width and the UUID-based dictionary identity to your storage layer's encoding stats. Omit STRUCT support (explicitly FIXME'd out upstream, :16-18).
