<!-- capsule-v2 -->
# art-operator-gate-delete-art — How does the ART distinguish "key exists" from "key exists but was deleted in this transaction"?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What protocol lets a unique-index append succeed when the duplicate row was deleted by the same uncommitted transaction?

## Connected graph-selected seam
**Path/Symbol:** `src/include/duckdb/execution/index/art/art_operator.hpp:InsertIntoInlined` (:335-373), gate-entry branch of `Insert` (:142-162); verification `src/execution/index/art/art.cpp:VerifyLeaf` (:866-943).
**Signature:** `static ARTConflictType InsertIntoInlined(ArenaAllocator &arena, ART &art, NodePtr &node, const ARTKey &key, const ARTKey &row_id, const idx_t depth, const GateStatus status, DeleteIndexInfo delete_index_info, IndexAppendMode append_mode)`.
**Data Shape:** `DeleteIndexInfo` carries optional list of companion delete-ARTs; each delete-art leaf is ALWAYS `LEAF_INLINED` keyed by key with the deleted ROW ID as payload. `IndexAppendMode ∈ {DEFAULT, IGNORE_DUPLICATES, INSERT_DUPLICATES}`.

### Decisive source
```cpp
	if (delete_index_info.delete_indexes) {
		// Lookup in the delete_art.
		for (auto &delete_index : *delete_index_info.delete_indexes) {
			auto &delete_art = delete_index.get().Cast<ART>();
			auto delete_leaf = Lookup(delete_art, delete_art.tree, key, 0);
			if (!delete_leaf) {
				continue;
			}

			// The row ID has changed.
			// Thus, the local index has a newer (local) row ID, and this is a constraint violation.
			D_ASSERT(delete_leaf.Get().GetType() == NType::LEAF_INLINED);
			auto deleted_row_id = delete_leaf.Get().GetRowId();
			auto this_row_id = node.GetRowId();
			if (deleted_row_id != this_row_id) {
				continue;
			}

			// The deleted key and its row ID match the current key and its row ID.
			Leaf::MergeInlined(arena, art, node, row_id_node, status, depth);
			return ARTConflictType::NO_CONFLICT;
		}
	}
```
and the unique-gate corruption tripwire:
```cpp
				throw FatalException("Corrupted unique ART index \"%s\": encountered an existing gated leaf in unique "
				                     "index while inserting",
				                     art.name);
```

**Flow:** append hits an existing inlined leaf on a UNIQUE index → normally CONSTRAINT. But if a delete-art contains THIS key whose stored row id equals the leaf's current row id, the old row is being deleted by this same transaction → re-inserting the key is legal (`MergeInlined`, NO_CONFLICT). Row-id mismatch means a DIFFERENT live row owns the key → keep searching other delete indexes, else constraint. VerifyLeaf mirrors this at verify time: matching deleted-row-id ⇒ return silently; FK fast-path uses MAX_ROW_ID since FK leaves are always inlined; non-inlined leaves scan exactly TWO row ids ("VerifyLeaf expects exactly two row IDs") — the transient DELETE+INSERT window documented in Insert's gate branch comment.
**Invariant:** The delete-art comparison is on ROW ID, not mere key presence — key-presence-only logic breaks UPDATE-in-transaction. Entering a GATE inside a unique main ART outside commit serialization is corruption (FatalException), not a normal path. Nested-leaf gates exist only for non-unique or delta indexes plus the documented two-row commit window.
**Probe:** `grep -n 'VerifyLeaf expects exactly two row IDs' src/execution/index/art/art.cpp` → line 924; `grep -n 'duplicate_key =' src/execution/index/art/art_merger.cpp` → line 30 (merge-side twin rule). Behavior pinned by `test/sql/index/art/constraints` suite and upsert tests under `test/sql/upsert`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "InsertIntoInlined delete_index_info VerifyLeaf conflict", limit: 8 });
```

## Verdict
Adopt the row-id-matched shadow-delete protocol and the two-row transient-window contract. Adapt to host MVEM visibility model. Omit FK MAX_ROW_ID fast path if host has no FK-on-index verification. Caveat: header-only file (art_operator.hpp) coverage freshness reads "missing" — resolve spans via search_graph before citing line numbers.
