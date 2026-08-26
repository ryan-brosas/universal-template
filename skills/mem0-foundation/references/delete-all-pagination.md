<!-- capsule-v2 -->
# Delete-all pagination — how do you delete a whole scope when the vector store silently caps list() pages?

**Source:** mem0 MIT `main@001c2352`; Codebase Memory `mem0`. **Question:** how does `delete_all` drain all memories of a scope without infinite loops or silent truncation?

## Connected graph-selected seam
**Path/Symbol:** `mem0/memory/main.py`: `delete_all` sync (:1890-1944) / async (:3540-3611); `DELETE_ALL_BATCH_SIZE = 1000` (:136); async-only `_bulk_clear_entity_store` (:2313-2332).
**Signature:** `delete_all(user_id=None, agent_id=None, run_id=None)` — top-level entity params ARE allowed here (unlike search/get_all); empty filter set raises and points to `reset()`.
**Data Shape:** loop state: `deleted_count`, `seen_batches: set[tuple[str, ...]]` of sorted id tuples; each page is up to 1000 rows.

### Decisive source
```python
# Keep listing after each batch is deleted. Most vector stores cap
# list() at 100 results by default, which silently truncates deletes.
while True:
    memories = self.vector_store.list(filters=filters, top_k=DELETE_ALL_BATCH_SIZE)[0]
    if not memories:
        break
    batch_ids = tuple(sorted(str(memory.id) for memory in memories))
    if batch_ids in seen_batches:
        logger.warning("Stopping delete_all after a repeated memory batch")
        break
    seen_batches.add(batch_ids)
    for memory in memories:
        self._delete_memory(memory.id)
```

**Flow:** re-list the SAME first page every iteration (deleting as you go shrinks it) → detect no-progress via the sorted-id-tuple fingerprint set → per-memory `_delete_memory` (history row with `is_deleted=1` + entity unlink). The ASYNC twin diverges deliberately: per-batch `asyncio.gather(..., return_exceptions=True)` with `skip_entity_cleanup=True` on every delete, then ONE final `_bulk_clear_entity_store(filters)` that wipes matching entity rows wholesale.
**Invariant:** always re-list instead of paginating forward (forward pagination breaks as deletions shift offsets); the repeated-batch guard terminates stores whose list ignores filters; async uses bulk-clear because concurrent read-modify-write of the same entities' `linked_memory_ids` lists races (comment-documented); partial failures are counted and warned, never raised.
**Probe:** `tests/test_main.py::test_delete_all_paginates_beyond_vector_store_page_size` (:299 — asserts 1001 deletes across 2 pages + terminal empty); `tests/test_memory.py::TestAsyncDeleteAllEntityRace::test_async_delete_all_bulk_clears_entity_store` (:1463).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mem0", query: "delete_all seen_batches repeated memory batch DELETE_ALL_BATCH_SIZE bulk_clear_entity_store", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the re-list-until-empty + repeated-batch-terminator loop verbatim; adopt the async bulk-clear-if-entity-store pattern wherever deletes fan out concurrently; adapt batch size to your store's real page cap.
