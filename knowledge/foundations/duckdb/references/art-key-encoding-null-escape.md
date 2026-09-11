<!-- capsule-v2 -->
# art-key-encoding-null-escape — What byte encoding makes ART keys order-preserving across types, NULLs, and compound columns?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How are heterogeneous typed values turned into comparable byte strings without ambiguity at boundaries?

## Connected graph-selected seam
**Path/Symbol:** `src/execution/index/art/art_key.cpp:CreateARTKey<string_t>` (:20-49), comparison operators (:112-132), `GetMismatchPos` (:159-168); NULL handling `src/execution/index/art/art.cpp:TemplatedGenerateKeys` (:265-284).
**Signature:** `ARTKey ARTKey::CreateARTKey(ArenaAllocator &allocator, string_t value)`; `bool ARTKey::operator>(const ARTKey &key) const`.
**Data Shape:** Key = raw bytes + length; VARCHAR keys get per-byte escaping plus a trailing `\0` terminator; compound keys are concatenations; an EMPTY key (`len==0`, default-constructed `ARTKey()`) encodes SQL NULL.

### Decisive source
```cpp
	// We escape \00 and \01.
	idx_t escape_count = 0;
	for (idx_t i = 0; i < string_len; i++) {
		if (string_data[i] <= 1) {
			escape_count++;
		}
	}

	idx_t key_len = string_len + escape_count + 1;
	...
	for (idx_t i = 0; i < string_len; i++) {
		if (string_data[i] <= 1) {
			// Add escape.
			key_data[pos++] = '\01';
		}
		key_data[pos++] = string_data[i];
	}

	// End with a null-terminator.
	key_data[pos] = '\0';
```
NULL reset in key-vector generation:
```cpp
		// We need to reset the key value in the reusable keys vector.
		keys[i] = ARTKey();
```

**Flow:** numeric/floating types are encoded big-endian order-preserving (see `Radix::EncodeData` / `EncodeFloat/EncodeDouble` tested in test_art_keys.cpp:210); strings escape every byte ≤ 0x01 as `\01` prefix-escape so embedded NULs cannot fake a terminator, then append real `\0` so 'hello' < 'hello\0' ordering holds. Compound keys concatenate column encodings; any NULL in ANY column resets the WHOLE key to empty (`ConcatenateKeys`: "A previous column entry was NULL" → skip; own NULL → `keys[i] = ARTKey()`), and empty keys are skipped by insert/delete/verify loops — SQL NULL is never indexed.
**Invariant:** Byte-comparison operators (`>`, `>=`) fall back to LENGTH comparison when prefixes tie (`return len > key.len;`) — that is what makes the terminator redundant-but-safe and keeps range scans correct for prefix keys. `GetMismatchPos` throws FatalException on identical row-id keys ("likely the same row id was inserted twice") rather than looping forever.
**Probe:** `grep -n 'escape_count' src/execution/index/art/art_key.cpp` → lines 26/29/33; behavior pinned by `test/sql/index/test_art_keys.cpp:57` TestKeys total-ordering matrix and `test/sql/index/art/scan/test_art_null_bytes.test` (`grep -c 'Duplicate key' ... → 2`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "CreateARTKey escape string_t ARTKey operator>", limit: 8 });
```

## Verdict
Adopt: ≤0x01 escaping + terminator, whole-key NULL semantics, length-tiebreak comparisons. Adapt type dispatch to host physical types. Omit legacy GEOMETRY conversion branches unless porting pre-v1.5 storage. Caveat: direct C++ tests cover ordering exhaustively; embedded-NUL behavior additionally covered by sqllogic test_art_null_bytes.
