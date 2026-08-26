<!-- capsule-v2 -->
# Worker idle loop — how do workers sleep without missing work while still returning memory to the allocator?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does the worker wait loop interleave timed waits with allocator flush/decay so idle threads release memory but never lose a wakeup?

## Timed-wait ladder: flush at 0.5s, decay-delay idle mark, untimed wait
**Path/Symbol:** `src/parallel/task_scheduler.cpp:TaskScheduler::ExecuteForever` (:159-213); constants `INITIAL_FLUSH_WAIT = 500000` mus (:161).
**Signature:** `while (*marker) { ... pool.Wait(...) ... }` — `marker` is an `atomic<bool>*` owned by the pool.
**Data Shape:** waits are in microseconds (`int64_t`); decay delay comes from `Allocator::DecayDelay()` as `optional_idx` seconds; allocator knobs are read live from settings (`AllocatorBackgroundThreadsSetting`, `AllocatorFlushThresholdSetting`).

### Decisive source
```cpp
if (!block_allocator.SupportsFlush()) {
    pool.Wait();                                   // plain untimed wait
} else if (!pool.Wait(INITIAL_FLUSH_WAIT)) {       // 0.5s timed wait expired => idle
    block_allocator.ThreadFlush(/*background=*/..., /*threshold=*/..., n_regular_threads);
    auto decay_delay = Allocator::DecayDelay();
    if (!decay_delay.IsValid()) {
        pool.Wait();                               // no decay: just wait again
    } else if (!pool.Wait(decay_seconds * 1000000 - INITIAL_FLUSH_WAIT)) {
        Allocator::ThreadIdle();                   // full decay elapsed: mark thread idle
        pool.Wait();
    }
}
```

**Flow:** wake → try dequeue/process → if nothing: wait(0.5s) → on timeout flush this thread's outstanding allocations → optionally wait the remainder of the decay window → mark `ThreadIdle()` → park forever until signaled.
**Invariant:** every `Wait` variant must be woken by `Signal` (enqueue side); the flush path is only entered when the timed wait EXPIRED (returned false), never after processing a task; on loop exit the thread flushes once more and marks itself idle before dying (:205-209).
**Probe:** `grep -c 'INITIAL_FLUSH_WAIT' src/parallel/task_scheduler.cpp` → `3`; `grep -n 'static constexpr int64_t INITIAL_FLUSH_WAIT = 500000' src/parallel/task_scheduler.cpp` → line 161.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "ExecuteForever INITIAL_FLUSH_WAIT ThreadFlush ThreadIdle", limit: 10 });
```

## Verdict
Adopt the expire-then-flush ladder (it decouples liveness from memory reclamation); adapt thresholds to your allocator's API; omit the Windows/GNU CPU-affinity plumbing around it.
