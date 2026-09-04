<!-- capsule-v2 -->
# Arena + intern pool — what memory discipline keeps per-file extraction allocation-free at teardown?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** When should you reach for an arena vs a slab vs plain malloc in a parser pipeline, and how do interned strings behave?

## Bump arena (64KB blocks) + pointer-identical interning
**Path/Symbol:** `src/foundation/arena.h` (contract 1–60) + `src/foundation/str_intern.h` (1–34).
**Signature:** `void *cbm_arena_alloc(CBMArena *a, size_t n);` / `const char *cbm_intern(CBMInternPool *pool, const char *s);`
**Data Shape:** Arena: ≤256 blocks, 64KB default block, 8-byte alignment, NO individual frees by design (per-file extraction shares one lifetime), `cbm_arena_reset()` keeps block 0 for reuse; sprintf helper clamps. Intern pool: arena storage + hash dedup ⇒ identical strings return IDENTICAL pointers; count/bytes tracked.

### Decisive source
```c
/* All memory is freed at once via cbm_arena_destroy(). Individual frees are
 * not supported — this is by design for per-file extraction where all data
 * has the same lifetime. */
...
/* Deduplicates strings: identical strings share a single allocation.
 * Returns stable pointers — safe to compare by pointer equality after interning. */
TEST(intern_dedup) {
    const char *s1 = cbm_intern(pool, "hello");
    const char *s2 = cbm_intern(pool, "hello");
    ASSERT_EQ((uintptr_t)s1, (uintptr_t)s2);
```

**Flow:** per-file or per-pass arena init → bump allocations for defs/uses/labels → intern identifiers for O(1) equality and dedup → reset between files or destroy at pass end → slab allocator (≤64B tier) optionally replaces tree-sitter's malloc on parsing threads.
**Invariant:** Never free individual arena allocations; never persist interning POINTERS beyond the pool's life when the pool may be destroyed (compare-by-pointer only within one pool epoch).
**Probe:** `tests/test_arena.c:arena_reset`, `arena_sprintf`; `tests/test_str_intern.c:intern_dedup`, `intern_n_with_length`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_arena_reset", limit: 5 });
```

## Verdict
Adopt same-lifetime arenas + interning for compiler-style passes; adapt block sizing; use the slab tier only when profiling shows tree-sitter-scale small-allocation churn.
