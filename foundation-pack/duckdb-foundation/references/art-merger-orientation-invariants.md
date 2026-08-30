<!-- capsule-v2 -->
# art-merger-orientation-invariants — What are the preconditions that make a lock-free structural ART merge safe, and where do duplicates surface?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** Why does the merger swap its arguments at specific points and how does gate status decide duplicate detection?

## Connected graph-selected seam
**Path/Symbol:** `src/execution/index/art/art_merger.cpp:Merge` (:19-77), `Emplace` (:79-101), `MergeNodes` (:166-208), `MergePrefixes` (:242-320).
**Signature:** `ARTConflictType Merge()` over an explicit stack of `(left NodePtr, right NodePtr, GateStatus status, idx_t depth)` entries; `void Emplace(NodePtr &left, NodePtr &right, const GateStatus parent_status, const idx_t depth)`.
**Data Shape:** Stack entry struct `NodeEntry`; conflict signal = `right_type == NType::LEAF_INLINED || entry.right.GetGateStatus() == GATE_SET` when `art.IsUnique()`.

### Decisive source
```cpp
		// Early-out due to a constraint violation.
		// If right is LEAF_INLINED, then left is also LEAF_INLINED.
		const auto duplicate_key =
		    right_type == NType::LEAF_INLINED || entry.right.GetGateStatus() == GateStatus::GATE_SET;
		if (art.IsUnique() && duplicate_key) {
			return ARTConflictType::CONSTRAINT;
		}
```
```cpp
	if (left_type == NType::LEAF_INLINED) {
		swap(left, right);
	} else if (left_type == NType::PREFIX && right_type != NType::LEAF_INLINED) {
		swap(left, right);
	}
```

**Flow:** Emplace normalizes orientation so `right` is always the "smaller" side: inlined leaves go right; prefixes go right (except against an inlined leaf). Entering a gate resets depth to 0 and promotes parent_status. The main loop dispatches on type pairs (inlined+inlined → Leaf::MergeInlined; node+inlined → fall back to ARTOperator::Insert with the ROW ID as key inside the gate; nested+nested → merge smaller into bigger byte-wise; internal+internal → extract children of right, free right FIRST, insert-or-recurse per byte — growth before Emplace is mandatory or references dangle). Prefix-vs-prefix walks to first differing byte → split into new Node4; identical → free right, descend both children; exhausted-one-side → continue via MergeNodeAndPrefix from max_count.
**Invariant:** "Merge smaller into bigger" (`GetType()` ordinal comparison + swap) preserves allocation-tier invariants; children extraction must complete BEFORE `FreeNode(right)` because arena validity — not heap lifetime — keeps copied nodes alive. Duplicate detection happens ONLY at leaf/gate contact points, so uniqueness checking cost scales with key overlap, not tree size.
**Probe:** `grep -n 'swap(left, right)' src/execution/index/art/art_merger.cpp` → lines 84/86 (+313); behavior pinned by index build paths exercising `test/sql/index/art/nodes/test_art_nested_leaf_coverage.test` and checkpoint-delta merges (`test/sql/index/art/storage/test_art_buffered_replays_chunk_edges.test`, 13 statement-ok blocks).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "ARTMerger Emplace MergeNodes MergePrefixes swap", limit: 8 });
```

## Verdict
Adopt: orientation normalization, extract-before-free ordering, gate-aware duplicate rule. Adapt node storage to host allocators. Omit deprecated-leaf merge branches (throws InternalException by design). Caveat: merger has no dedicated C++ unit test; covered transitively by every parallel CREATE INDEX and buffered-replay sqllogic test.
