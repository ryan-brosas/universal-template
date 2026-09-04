<!-- capsule-v2 -->
# Arena eager-commit gating — why does mimalloc's arena commit policy need an OS-cost check?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you stop allocator arenas from exploding the process's mmap count on Linux?

## Eager-commit arenas only where OS commit is cheap
**Path/Symbol:** `src/foundation/mem.c:290–315`.
**Signature:** mimalloc option configuration inside `cbm_mem_init` (option value 2 = "eager-commit arenas only on an OS that commits cheaply").
**Data Shape:** Symptom: with mimalloc serving sqlite+tree_sitter populations, a Linux index worker peaked at ~22k VM mappings; some allocators' arena growth maps per-arena and `mmap` failing for ANY size manifests as "cannot allocate" long before RAM exhaustion.

### Decisive source
```c
/* ... pay it for every allocation in the process. mimalloc commits a range with
 * ... mimalloc only served the bound populations (sqlite, tree_sitter) that was a
 * ... mimalloc on Linux, an index worker peaked at ~22k mappings against
 * ... which mmap fails for ANY size — hence mimalloc reporting it "cannot
 * ... mimalloc's own default is 2, meaning "eager-commit arenas only on an OS
 * [where committing is cheap]" */
```

**Flow:** init → consult OS commit cost → set mimalloc's eager-arena-commit option accordingly → worker mapping counts stay bounded → diagnostics census verifies via arena slices rather than RSS alone.
**Invariant:** Allocator tuning must be conditioned on measured kernel behavior (mapping count), not assumed from documentation; "cannot allocate" can mean too-many-mappings, not out-of-memory.
**Probe:** `tests/test_mem.c:mem_arena_eager_commit_follows_platform_commit_cost` plus mem_rss_tracking; live evidence via diagnostics arena dumps.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "eager", limit: 5 });
```

## Verdict
Adopt platform-gated allocator options when your embedder owns allocation-heavy subsystems; adapt thresholds to kernels; keep the census-based verification loop.
