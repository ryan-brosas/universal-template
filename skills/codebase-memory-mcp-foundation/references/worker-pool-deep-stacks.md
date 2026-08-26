<!-- capsule-v2 -->
# Worker pool — how do you parallelize AST-heavy work without GCD stack overflows?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What backend and scheduling shape keep deep-recursion parsers safe while load-balancing across heterogeneous cores?

## pthreads + 8MB stacks + atomic work-stealing index
**Path/Symbol:** `src/pipeline/worker_pool.c` (module, 1–90) + `src/foundation/system_info.c:cbm_default_worker_count` (283–306).
**Signature:** `void cbm_parallel_for(int count, cbm_parallel_fn fn, void *ctx, cbm_parallel_for_opts_t opts);`
**Data Shape:** Workers pull indices via `atomic_fetch_add_explicit(&next_idx, 1, memory_order_relaxed)`; serial fallback when count ≤1 or workers ≤1; stacks pinned at 8 MB (`CBM_WORKER_STACK_SIZE`), matching the main thread. Worker counts: initial indexing uses ALL cores; incremental leaves one headroom core; `CBM_WORKERS` env overrides clamped to [1, CBM_WORKERS_MAX].

### Decisive source
```c
/* Backend: pthreads with 8MB stacks and atomic work-stealing index.
 * GCD is avoided because its worker threads have 512KB stacks,
 * which overflows on deeply nested ASTs (tree-sitter + walk_defs).
 * Each worker pulls from a shared atomic counter — zero
 * contention, natural load balancing across heterogeneous cores. */
```

**Flow:** compute default workers (env override > sysconf) → spawn N pthreads with explicit large stacks → each loops fetch-add on the shared counter until exhausted → join → per-file results merge in deterministic worker-slot order at a higher layer (see edge-props capsule for why order must not matter anyway).
**Invariant:** Stack size is a correctness knob, not a tuning knob — tree-sitter GLR merges recurse per nesting level; relaxed ordering suffices because index uniqueness is the only requirement.
**Probe:** `tests/test_worker_pool.c` (index-visited-exactly-once contract) and `tests/test_parallel.c:parallel_calls_parity` family pinning seq-vs-par edge-count equality.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_parallel_for", limit: 5 });
```

## Verdict
Adopt explicit-stack pthreads with atomic index dispatch for recursive-parser fan-out; adapt worker defaults to your cgroup awareness needs; omit the force-pthreads compat flag if you have no legacy callers.
