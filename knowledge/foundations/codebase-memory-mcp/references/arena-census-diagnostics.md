<!-- capsule-v2 -->
# Arena census diagnostics — how do you prove an allocator is healthy instead of guessing from RSS?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** When RSS stays high, what per-arena evidence distinguishes retention from commit behavior?

## Free-committed vs free-reserved vs free-purgeable legend
**Path/Symbol:** `src/foundation/diagnostics.c` arena slice map (~200–225) + rationale in store.c page-cache slab comment (755–775) + mem.c eager-commit notes (290–315).
**Signature:** `mi_register_output(diag_stats_write, sink);` redirecting mimalloc's own output into the private stats file; slice map legend: `_` free-committed (retained), `.` free-reserved (returned to OS), `~` free-purgeable.
**Data Shape:** Census answers: zero free-committed slices + high % returned ⇒ allocator CORRECT and the problem is allocation SHAPE; conversely retained `_` regions localize the leak to specific arena state. Linux mmap-count pressure (~22k mappings/worker) motivated eager-commit gating by OS commit cost.

### Decisive source
```c
/* mi_debug_show_arenas writes through mimalloc's own output hook, so redirect
 * that into this file. */
(void)fputs("\n--- arenas ---\n", sink);
...
/* The arena census confirmed the allocator was behaving correctly: zero
 * free-committed slices, 58% already returned to the OS. The problem was
 * allocation SHAPE, not retention. */
```

**Flow:** enable diagnostics → periodic or on-demand dump writes allocator stats + arena map via the registered output hook → operator/agent reads the legend to classify retention-vs-shape → fixes target allocation patterns (e.g., dedicated slab) rather than purges.
**Invariant:** Never diagnose from process totals alone — pool-level slices with a three-state legend are the minimum evidence for a retention claim.
**Probe:** `tests/test_diagnostics.c:diagnostics_outputs_are_owner_private_regular_files`, `mem_collect_reclaims` in tests/test_mem.c; soak discovery via tests/test_diagnostics.c:300.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "mi_register_output", limit: 5 });
```

## Verdict
Adopt hook-redirected arena dumps with an explicit legend before blaming your allocator; adapt to jemalloc/mimalloc equivalents; omit eager-commit tuning on platforms with cheap commits.
