<!-- capsule-v2 -->
# art-prefix-split-gate-status — What does prefix splitting return, and why is its GateStatus result load-bearing?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does splitting a compressed path at byte N preserve both the remaining path AND gate identity?

## Connected graph-selected seam
**Path/Symbol:** `src/execution/index/art/prefix.cpp:Split` (:122-180); callers `art_operator.hpp:InsertIntoPrefix` (:399-412), `art_merger.cpp:MergePrefixes` (:282-291).
**Signature:** `GateStatus Prefix::Split(ART &art, reference<NodePtr> &node_ref, NodePtr &child, const uint8_t pos)`.
**Data Shape:** Prefix node = bytes[0..count) + data[count] count slot + child_slot. Three structural cases: split inside a full prefix, split mid-prefix, split at last byte of a non-full prefix.

### Decisive source
```cpp
	// No bytes left before the split, free this node.
	if (pos == 0) {
		auto old_status = node_ref.get().GetGateStatus();
		NodePtr::FreeNode(art, node_ref);
		return old_status;
	}

	// There are bytes left before the split.
	// The subsequent node replaces the split byte.
	node_ref = *prefix.child_slot;
	return GateStatus::GATE_NOT_SET;
```
caller side:
```cpp
	NodePtr child;
	const auto split_status = Prefix::Split(art, node_ref, child, cast_pos);

	Node4::New(art, node_ref);
	node_ref.get().SetGateStatus(split_status);
```

**Flow:** Split truncates this prefix to bytes[0..pos), hands back the suffix chain in `child`, and returns the gate status that must decorate whatever node ends up at the split position: freeing the original node (pos==0 case) means its GATE flag would vanish unless returned and re-applied to the replacement; otherwise a fresh Node4 takes the split position with GATE_NOT_SET. The full-prefix special case (pos+1 == PrefixCount) decrements count and aliases node_ref to the existing child instead of allocating. Callers MUST call SetGateStatus(split_status) on the newly created node — InsertIntoPrefix does, MergePrefixes does (`left_ref.get().SetGateStatus(status)`).
**Invariant:** A gate marks "this subtree enumerates row ids" — dropping it on split makes lookups treat nested row-id paths as key bytes (silent corruption); keeping it when the split consumed the gate makes every key under it appear duplicated. Append semantics (`Append` merges continuation prefix chains) exist precisely so splits stay shallow.
**Probe:** `grep -n 'return old_status' src/execution/index/art/prefix.cpp` → line 71; `grep -n 'SetGateStatus(split_status)' src/include/duckdb/execution/index/art/art_operator.hpp` → line 408. Behavior pinned by `test/sql/index/art/nodes/test_art_prefix_edge_cases.test_slow`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "Prefix Split Reduce NewInternal gate status", limit: 8 });
```

## Verdict
Adopt the three-case split skeleton and the return-and-reapply gate contract verbatim. Adapt node allocation to host. Omit full-prefix aliasing micro-optimization only if host prefixes are unbounded. Caveat: covered by prefix edge-case sqllogic test (.test_slow); no isolated C++ unit test.
