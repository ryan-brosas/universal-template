<!-- capsule-v2 -->
# art-merge-buffer-id-remap — Why must a deserialized ART be traversed before its allocators merge into another ART?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What breaks if you concatenate two ARTs' node allocators without rewriting pointers first?

## Connected graph-selected seam
**Path/Symbol:** `src/execution/index/art/art.cpp:MergeIndexes` (:1318-1353), `InitializeMergeUpperBounds` (:1266-1271), `InitializeMerge` (:1273-1316).
**Signature:** `bool MergeIndexes(IndexLock &state, BoundIndex &source_index)`; `void InitializeMerge(NodePtr &other_tree, unsafe_vector<idx_t> &upper_bounds)`.
**Data Shape:** Node pointers encode (buffer_id, offset) per allocator type; `upper_bounds[allocator_idx] = allocator->GetUpperBoundBufferId()` captured BEFORE any merge; 9 allocators (`ALLOCATOR_COUNT`, art.hpp:45) covering prefix, leaf, node4/16/48/256, node7/15/256-leaf.

### Decisive source
```cpp
	if (other_art.owns_data) {
		if (prefix_count != other_art.prefix_count) {
			throw InternalException("Failed to merge ARTs - prefix count does not match");
		}
		if (tree.HasMetadata()) {
			// Fully deserialize other_index, and traverse it to increment its buffer IDs.
			unsafe_vector<idx_t> upper_bounds;
			InitializeMergeUpperBounds(upper_bounds);
			other_art.InitializeMerge(other_art.tree, upper_bounds);
		}

		// Merge the node storage.
		for (idx_t i = 0; i < allocators->size(); i++) {
			(*allocators)[i]->Merge(*(*other_art.allocators)[i]);
		}
	}
```
with the in-place pointer rewrite:
```cpp
		auto original = child;
		// remap BufferId in-place within the parent.
		auto idx = NodePtr::GetAllocatorIdx(type);
		child.IncreaseBufferId(upper_bounds[idx]);
```

**Flow:** only DESERIALIZED sources (owning their data) need remap: traverse the source tree preorder, add the destination's current buffer-id upper bound to every non-inlined node's buffer id IN PLACE in its parent slot, push originals for internal nodes only (leaves have no children). Then append each source allocator's buffers onto the destination's. Finally structural ARTMerger merges the trees. If destination tree is empty, skip traversal and adopt `other_art.tree` wholesale after allocator merge (`tree = other_art.tree; other_art.tree.Clear()`).
**Invariant:** Upper bounds must be read BEFORE appending buffers; traversal must complete BEFORE allocator Merge; prefix_count must match or sizes computed at construction diverge (explicit InternalException). The empty-destination fast path still clears the source tree so a double merge cannot double-free.
**Probe:** `grep -n 'IncreaseBufferId' src/execution/index/art/art.cpp` → line 1290; `grep -n 'Failed to merge ARTs' src/execution/index/art/art.cpp` → line 1326. Behavior pinned by checkpoint-delta merge tests: `grep -c 'statement ok' test/sql/index/art/storage/test_art_buffered_replays_chunk_edges.test` → 13.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "InitializeMerge IncreaseBufferId upper_bounds MergeIndexes", limit: 8 });
```

## Verdict
Adopt the remap-before-concatenate ordering and the owns-data gating. Adapt pointer encoding to host node handles. Omit deprecated-leaf throw branch when porting modern storage only. Caveat: exercised via storage replay suite rather than isolated unit test.
