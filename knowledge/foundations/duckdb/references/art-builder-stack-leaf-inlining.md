<!-- capsule-v2 -->
# art-builder-stack-leaf-inlining — How does a sorted key array become an ART without per-key tree walks?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What does the bulk builder exploit about sortedness, and where do unique violations surface during construction?

## Connected graph-selected seam
**Path/Symbol:** `src/execution/index/art/art_builder.cpp:Build` (:10-89); entry `ART::Build` (`art.cpp:492-513`).
**Signature:** `ARTConflictType Build()` over stack entries `(node NodePtr, start idx_t, end idx_t, depth idx_t)`; init `builder.Init(tree, row_count - 1)`.
**Data Shape:** `keys`/`row_ids` are parallel `unsafe_vector<ARTKey>`; PRECONDITION: keys sorted (guaranteed by the sorted build path). `entry.end - entry.start + 1` = row count sharing a full-key prefix.

### Decisive source
```cpp
		// Increment the depth until we reach a leaf or find a mismatching byte.
		auto prefix_depth = entry.depth;
		while (start.len != entry.depth && start.ByteMatches(end, entry.depth)) {
			entry.depth++;
		}

		// True, if we reached a leaf: all bytes of start_key and end_key match.
		if (start.len == entry.depth) {
			// Get the number of row IDs in the leaf.
			auto row_id_count = entry.end - entry.start + 1;
			if (art.IsUnique() && row_id_count != 1) {
				return ARTConflictType::CONSTRAINT;
			}
```
and child partitioning:
```cpp
		vector<idx_t> child_offsets;
		child_offsets.emplace_back(entry.start);
		for (idx_t i = entry.start + 1; i <= entry.end; i++) {
			if (keys[i - 1].data[entry.depth] != keys[i].data[entry.depth]) {
				child_offsets.emplace_back(i);
			}
		}
```

**Flow:** compare ONLY first-vs-last key of the range to find common prefix depth (sortedness makes interior keys share it); full match → leaf with prefix; single row → inline it directly; multiple rows on a UNIQUE index → CONSTRAINT immediately (duplicates are adjacent when sorted — that is the whole trick). Multi-row non-unique → gate leaf inserting each row id via ARTOperator (row ids NOT sorted inside gate). Otherwise create prefix, partition range by byte changes at current depth into minimal node type (`NodePtr::GetInternalNodeType(child_offsets.size())`), push each subrange. Stack empties → NO_CONFLICT.
**Invariant:** Duplicate detection costs O(1) per duplicate run because equal keys are contiguous post-sort — a builder over UNSORTED input silently produces wrong trees (the builder comment at :49-50 notes row ids specifically "are not sorted", which is why gate insertion goes through the operator). InsertChild must precede fetching the mutable child slot (`GetChildMutable(..., true)`).
**Probe:** `grep -n 'row_id_count != 1' src/execution/index/art/art_builder.cpp` → line 34; `grep -n 'row IDs are not sorted' src/execution/index/art/art_builder.cpp` → line 49. Behavior pinned via `test/sql/create/index` bulk builds and float ordering matrix `test/sql/index/test_art_index.cpp:212` ("ART Floating Point").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "ARTBuilder Build child_offsets ByteMatches", limit: 8 });
```

## Verdict
Adopt the sorted-range divide-and-conquer skeleton and adjacency-based uniqueness check. Adapt node-type selection to host fanout tiers. Omit the DEBUG full-scan verification in ART::Build. Caveat: no isolated unit test for the builder; exercised through every CREATE INDEX on sorted paths.
