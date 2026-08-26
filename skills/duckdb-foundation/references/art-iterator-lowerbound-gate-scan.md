<!-- capsule-v2 -->
# art-iterator-lowerbound-gate-scan — How does a range scan position itself exactly at the lower bound, and how do nested row-id leaves interleave?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the resumable scan protocol that yields ordered row IDs across three different leaf representations without missing or duplicating entries?

## Connected graph-selected seam
**Path/Symbol:** `src/execution/index/art/iterator.cpp:LowerBound` (:193-279), `Scan<Output>` template (:47-128), `FindMinimum` (:134-191), gate bookkeeping in `PopNode` (:319-349).
**Signature:** `template <typename Output> ARTScanResult Scan(const ARTKey &upper_bound, Output &output, bool equal)`; `bool LowerBound(NodePtr current, const ARTKey &key, const bool equal)`.
**Data Shape:** Iterator stack `nodes` of (NodePtr, byte); `current_key` byte stack; `nested_depth` + `row_id[ROW_ID_SIZE]` active INSIDE a gate; `resume_state` (cached deprecated-leaf ids, nested_byte, nested_started) enabling PAUSED/COMPLETED protocol; outputs are policy types (`RowIdSetOutput`, `KeyRowIdOutput`).

### Decisive source
```cpp
		// Compare the copied prefix bytes with the key bytes.
		for (idx_t i = 0; i < prefix_count; i++) {
			// We found a prefix byte that is less than its corresponding key byte.
			// I.e., the subsequent node is lesser than the key. Thus, the next node
			// is the lower bound.
			if (current_key[prefix_offset + i] < key[depth + i]) {
				return Next();
			}

			// We found a prefix byte that is greater than its corresponding key byte.
			// I.e., the subsequent node is greater than the key. Thus, the minimum is
			// the lower bound.
			if (current_key[prefix_offset + i] > key[depth + i]) {
				FindMinimum(prefix_child);
				return true;
			}
		}
```
Gate handling inside FindMinimum:
```cpp
		if (current.GetGateStatus() == GateStatus::GATE_SET) {
			D_ASSERT(status == GateStatus::GATE_NOT_SET);
			status = GateStatus::GATE_SET;
			entered_nested_leaf = true;
			nested_depth = 0;
		}
```

**Flow:** LowerBound walks root→leaf matching key bytes; on a child-byte GREATER than the key byte it snaps to FindMinimum(child) (everything below is ≥ bound); on LESS it advances via Next(); at an exact leaf with `equal==false` and full containment it steps Next() once to exclude the bound itself. Entering a GATE resets depth and mirrors every traversed byte into `row_id[]` — the row id IS reconstructed from the nested path (8 bytes). Scan emits per leaf kind: LEAF_INLINED one id; deprecated LEAF drains cached chain ids; NODE_7/15/256_LEAF iterate bytes into the LAST byte of the row-id buffer. Every emission checks `output.IsFull()` FIRST, returning PAUSED with resume_state positioned to continue exactly where it left off.
**Invariant:** Upper-bound checking is suppressed while inside a gate or after entering a nested leaf (`status == GATE_NOT_SET || entered_nested_leaf` guard) because the nested subtree enumerates ROW IDS of one key, not keys. PopNode decrements `nested_depth` symmetrically and restores gate status on gate-pop. Breaking this mirror corrupts every subsequent row id.
**Probe:** `grep -n 'row_id\[nested_depth\]' src/execution/index/art/iterator.cpp` → lines 161, 182; behavior pinned by `test/sql/index/art/scan/test_art_range_scan.test`, `test_art_many_matches.test`, `test_art_scan_normal_to_nested.test`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "Iterator LowerBound FindMinimum nested_depth gate", limit: 8 });
```

## Verdict
Adopt: prefix-compare snap logic, equal-exclusion step, gate depth mirroring, PAUSED/resume contract. Adapt output policies to host consumers. Omit deprecated LEAF chain caching if the host storage never writes v1.0 leaves. Caveat: iterator.cpp fully indexed; scan suite covers normal/nested/adaptive/threshold cases.
