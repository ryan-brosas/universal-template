<!-- capsule-v2 -->
# art-sorted-parallel-build-merge — Why does the index build sort keys, and what is the exact local→global merge protocol?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How is a bulk ART constructed in parallel without lock contention and how do duplicate keys surface?

## Connected graph-selected seam
**Path/Symbol:** `src/execution/index/art/art_index.cpp:ARTBuildSinkSorted` (:111-128), `ARTBuildCombine` (:148-155); conflict mapping `ART::MergeIndexes` (`art.cpp:1318-1353`).
**Signature:** `void ARTBuildSink(IndexBuildSinkInput &input, DataChunk &key_chunk, DataChunk &row_chunk)`; `bool ARTBuildCombine(IndexBuildCombineInput &input)`.
**Data Shape:** Per-thread `ARTBuildLocalState`: own `BoundIndex`(ART) + `ArenaAllocator` + reusable `unsafe_vector<ARTKey>` key/rowid vectors (STANDARD_VECTOR_SIZE). Global state holds the single global ART. `ARTBuildBindData.sorted = true` always (new sort implementation handles VARCHAR/multi-column).

### Decisive source
```cpp
	// Construct an ART for this chunk.
	auto art = make_uniq<ART>(input.info.GetIndexName(), l_index->GetConstraintType(), l_index->GetColumnIds(),
	                          l_index->table_io_manager, l_index->unbound_expressions, storage.db,
	                          l_index->Cast<ART>().allocators);
	if (art->Build(l_state.keys, l_state.row_ids, key_chunk.size()) != ARTConflictType::NO_CONFLICT) {
		throw ConstraintException("Data contains duplicates on indexed column(s)");
	}

	// Merge the ART into the local ART.
	if (!l_index->MergeIndexes(*art)) {
		throw ConstraintException("Data contains duplicates on indexed column(s)");
	}
```
and Combine:
```cpp
	if (!gstate.global_index->MergeIndexes(*lstate.local_index)) {
		throw ConstraintException("Data contains duplicates on indexed column(s)");
	}
```

**Flow:** sink generates key vectors per chunk; sorted path bulk-builds a THROWAWAY chunk-local ART via the stack-based builder (`ART::Build` → `ARTBuilder`, which detects uniqueness violations when a leaf accumulates >1 row id on a unique index), merges it into the thread-local ART (`MergeIndexes` returns false on duplicate-key conflict during structural merge), then Combine merges each thread-local ART into the global one. EVERY failure point — builder conflict, local merge false, combine merge false — maps to the SAME `ConstraintException("Data contains duplicates on indexed column(s)")`. Unsorted path exists as fallback inserting row-by-row via `ARTOperator::Insert`.
**Invariant:** Merges are conflict-detected boolean operations, not exceptions, at every tier; allocators are SHARED between chunk ARTs and their local parent (constructor takes `l_index->Cast<ART>().allocators`) so buffer-id remapping during merge stays coherent. The build never mutates the global ART from worker threads — contention-free by construction.
**Probe:** `grep -n 'ARTBuildSinkSorted' src/execution/index/art/art_index.cpp` → lines 111/140; `grep -n 'prefix_count != other_art.prefix_count' src/execution/index/art/art.cpp` → 1325 (merge precondition). Behavior pinned by `test/sql/create/index` conventions and `test/sql/index/test_art_index.cpp:10` rollback test for the append path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "ARTBuildSinkSorted MergeIndexes IndexBuildGlobalState", limit: 8 });
```

## Verdict
Adopt: per-chunk throwaway structure + two-tier conflict-detected merge + uniform constraint-error mapping. Adapt to host parallel-build sink interfaces. Omit the legacy unsorted path if the host always sorts. Caveat: art_index.cpp coverage clean; no direct unit test for ARTBuildSinkSorted itself — exercised via CREATE INDEX sqllogic suites.
