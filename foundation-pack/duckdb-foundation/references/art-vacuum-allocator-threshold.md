<!-- capsule-v2 -->
# art-vacuum-allocator-threshold — When does the ART reclaim dead node slots, and why is gate status preserved across relocation?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What triggers a vacuum pass and what must survive pointer relocation?

## Connected graph-selected seam
**Path/Symbol:** `src/execution/index/art/art.cpp:Vacuum` (:1215-1260), `VacuumPointerIfNeeded` (:1196-1213), `InitializeVacuum` (:1182-1188).
**Signature:** `void Vacuum(IndexLock &state)`; child_handler/on_pop lambdas feeding `ARTScanPreorder`.
**Data Shape:** `unordered_set<uint8_t> indexes` = allocator indices whose `InitializeVacuum()` returned true (segment fill ≥ threshold); each allocator tracks NeedsVacuum per pointer; `NodePtr` metadata byte carries type bits + AND_GATE (0x80) flag.

### Decisive source
```cpp
	const auto status = node.GetGateStatus();
	node = allocator.VacuumPointer(node);
	node.SetMetadata(static_cast<uint8_t>(type));
	node.SetGateStatus(status);
```
and the traversal contract:
```cpp
	auto on_pop = [&](NodePtr current) -> ARTScanNodeResult {
		D_ASSERT(current.HasMetadata());
		if (current.GetType() == NType::LEAF) {
			if (vacuum_deprecated_leaves) {
				// Vacuum the internal pointers in the deprecated leaf chain.
				Leaf::DeprecatedVacuum(art, current);
			}
			return ARTScanNodeResult::SKIP;
		}
		return ARTScanNodeResult::SCAN_CHILDREN;
	};
```

**Flow:** Vacuum first asks every allocator whether it needs reclaiming (only those enter `indexes`); empty tree → reset everything and return. Preorder scan rewrites qualifying parent slots in place (`node = allocator.VacuumPointer(node)` returns relocated pointer), then RESTORES type byte and gate status — relocation loses the metadata high bits, so both writes are mandatory. Deprecated leaves optionally vacuum their internal chains then SKIP subtree descent (leaves have no children to traverse). FinalizeVacuum commits allocator-side compaction.
**Invariant:** Gate status lives in the SAME metadata byte as node type (`GetMetadata() & AND_GATE`); any code that moves a NodePtr and rewrites only the pointer value corrupts nested-leaf identity. LEAF_INLINED pointers are never vacuumed (no allocation behind them). Vacuum runs under the index lock and only when `owns_data`.
**Probe:** `grep -n 'node.SetGateStatus(status)' src/execution/index/art/art.cpp` → line 1212; behavior pinned by memory-pressure suite `test/sql/index/art/memory/test_art_linear.test_slow` (vacuum exercised at allocator thresholds).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "Vacuum VacuumPointerIfNeeded InitializeVacuum allocator", limit: 8 });
```

## Verdict
Adopt: threshold-gated allocator set, in-place slot rewrite with metadata+gate restoration, leaf-skip traversal. Adapt FixedSizeAllocator semantics to host arena. Omit deprecated-leaf chain vacuum for modern-only storage. Caveat: .test_slow coverage means CI-light; treat threshold values as tunable, the restoration order as invariant.
