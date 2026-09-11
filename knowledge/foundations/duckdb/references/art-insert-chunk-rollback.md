<!-- capsule-v2 -->
# art-insert-chunk-rollback — How does a multi-row insert into a unique ART stay atomic when row 700 duplicates?

**Source:** duckdb MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What must an index implementation do to the already-inserted prefix of a chunk after a mid-chunk constraint violation?

## Connected graph-selected seam
**Path/Symbol:** `src/execution/index/art/art.cpp:InsertKeys` (:537-591), rollback loop (:557-567).
**Signature:** `ErrorData InsertKeys(ArenaAllocator &arena, unsafe_vector<ARTKey> &keys, unsafe_vector<ARTKey> &row_id_keys, idx_t row_count, const DeleteIndexInfo &delete_info, IndexAppendMode append_mode, optional_ptr<DataChunk> chunk)`.
**Data Shape:** `conflict_type ∈ {NO_CONFLICT, CONSTRAINT, ...}`; `optional_idx conflict_idx` records the offending row; `was_empty = !tree.HasMetadata()` snapshot taken BEFORE any insert.

### Decisive source
```cpp
	// Remove any previously inserted entries.
	if (conflict_type != ARTConflictType::NO_CONFLICT) {
		D_ASSERT(conflict_idx.IsValid());
		for (idx_t i = 0; i < conflict_idx.GetIndex(); i++) {
			if (keys[i].Empty()) {
				continue;
			}
			D_ASSERT(tree.GetGateStatus() == GateStatus::GATE_NOT_SET);
			ARTOperator::Delete(*this, tree, keys[i], row_id_keys[i]);
		}
	}
```
and the error surface:
```cpp
	if (conflict_type == ARTConflictType::CONSTRAINT) {
		// chunk is only null when called from MergeCheckpointDeltas.
		auto msg = chunk ? AppendRowError(*chunk, conflict_idx.GetIndex()) : string("???");
		return ErrorData(ConstraintException("PRIMARY KEY or UNIQUE constraint violation: duplicate key \"%s\"", msg));
	}
```

**Flow:** insert rows sequentially; on first non-NO_CONFLICT stop immediately; DELETE every previously inserted key/row-id pair of this chunk in order; only then raise with the offending row's value rendered (`AppendRowError`). Empty keys (NULLs) are skipped both in insert and undo. The gate-status assert documents that main-tree rollback never runs inside a nested leaf.
**Invariant:** The caller-visible effect is all-or-nothing per chunk — but the mechanism is compensating deletes, not transactional isolation. A porter who skips the compensation loop corrupts the index permanently (phantom keys blocking future inserts); a porter who raises before stopping the loop deletes rows it never inserted. `IndexAppendMode::IGNORE_DUPLICATES` and delete-art shadow checks (see art-operator-gate-delete-art capsule) alter conflict classification upstream in `InsertIntoInlined`.
**Probe:** `grep -n 'Remove any previously inserted entries' src/execution/index/art/art.cpp` → line 557; behavior pinned by `test/sql/index/test_art_index.cpp:10` "Test ART index with rollbacks" (BEGIN/INSERT/COMMIT-or-ROLLBACK ×10k then exact COUNT via index scan).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "InsertKeys conflict rollback ARTOperator Delete chunk", limit: 8 });
```

## Verdict
Adopt the stop-at-first-conflict + ordered-compensating-delete protocol and the was_empty debug verification hook. Adapt error rendering. Omit DEBUG post-conditions. Caveat: direct C++ test covers transactional rollback through the public API, not InsertKeys in isolation.
