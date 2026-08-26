<!-- capsule-v2 -->
# Memory limit resize — how do you shrink a live memory budget that may be un-shrinkable?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the safe protocol for lowering `memory_limit` while queries hold pinned buffers?

## Evict-first-then-commit; roll back the limit if post-commit eviction fails
**Path/Symbol:** `src/storage/buffer/buffer_pool.cpp:BufferPool::SetLimit` (:522-542); under `lock_guard<mutex> l_lock(limit_lock)` (:523).
**Signature:** `void SetLimit(idx_t limit, const char *exception_postscript)`; throws `OutOfMemoryException("Failed to change memory limit to %lld: could not free up enough memory for the new limit%s", ...)`.
**Data Shape:** `maximum_memory` is the committed budget; `postscript` appends engine-specific remediation text (e.g. the in-memory-mode hint) to both failure messages.

### Decisive source
```cpp
if (!EvictBlocks(QueryContext(), MemoryTag::EXTENSION, 0, limit).success)
    throw OutOfMemoryException(...);            // pre-check under OLD limit
idx_t old_limit = maximum_memory;
maximum_memory = limit;                          // commit
if (!EvictBlocks(QueryContext(), MemoryTag::EXTENSION, 0, limit).success) {
    maximum_memory = old_limit;                  // roll back
    throw OutOfMemoryException(...);
}
block_allocator.FlushAll();                      // only on full success
```

**Flow:** try evicting toward the new ceiling → if impossible, fail without touching state → commit the new maximum → evict AGAIN (buffers freed by the first pass may now be reclaimable; also catches races) → any failure restores the old limit and throws → success ends with a global allocator flush.
**Invariant:** the limit variable must never describe an unreachable state — every failure path leaves it byte-identical to entry; both eviction passes run under `limit_lock`, serializing concurrent resizes.
**Probe:** `grep -c 'EvictBlocks(QueryContext(), MemoryTag::EXTENSION, 0, limit)' src/storage/buffer/buffer_pool.cpp` → `2`; `grep -c 'maximum_memory = old_limit' src/storage/buffer/buffer_pool.cpp` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "SetLimit OutOfMemoryException exception_postscript limit_lock FlushAll", limit: 10 });
```

## Verdict
Adopt trial-eviction/commit/re-verify with rollback for runtime budget changes; adapt the tag you evict under and message wording; omit the allocator flush hook if your allocator self-manages.
