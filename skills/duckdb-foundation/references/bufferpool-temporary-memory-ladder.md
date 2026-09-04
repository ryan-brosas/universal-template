<!-- capsule-v2 -->
# Temporary memory manager — how do you split a query memory budget among concurrent operators?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What is the reservation ladder for a `TemporaryMemoryState`, and when is the gradient-descent splitter used instead of simple bounds?

## Five-arm UpdateState ladder; derivative-guided fair share under pressure
**Path/Symbol:** `src/storage/temporary_memory_manager.cpp:TemporaryMemoryManager::UpdateState` (:126-167), `ComputeReservation` (:228-348), `ComputeDerivatives` (:194-226); constants in `temporary_memory_manager.hpp` — `MAXIMUM_MEMORY_LIMIT_RATIO = 0.9` (:89), `MAXIMUM_FREE_MEMORY_RATIO = 0.9` (:91), remaining-state reservations 8..32 (:93-94).
**Signature:** `void UpdateState(ClientContext&, TemporaryMemoryState&)`; per-thread minimum = `min(num_threads * 512 * BLOCK_ALLOC_SIZE, memory_limit / 16)` (`DefaultMinimumReservation` :74-77).
**Data Shape:** state carries `remaining_size` (work left), `minimum_reservation`, `materialization_penalty`; the manager keeps running totals and an `active_states` set, all mutated under one annotated lock.

### Decisive source
```cpp
if (remaining == 0)            SetReservation(state, 0);          // end-of-state
else if (DebugForceExternal)   SetReservation(state, lower_bound); // force minimum
else if (!has_temporary_directory)
                               SetReservation(state, remaining);   // cannot offload: no cap
else if (overshoots_limit)     SetReservation(state, lower_bound); // "We overshot"
else {
    upper = min(remaining, query_max_memory,
                MAXIMUM_FREE_MEMORY_RATIO * free_memory, free_memory);
    new_reservation = lower >= upper ? lower
                    : remaining_size > memory_limit ? ComputeReservation(state)  // optimizer
                    : upper;
}
```

**Flow:** register (seed with default minimum) → update on progress → trivial arms first → else bound by free memory and, only when the operator's remaining work EXCEEDS all of memory, run the throughput-geomean gradient loop that distributes free memory to the lowest-derivative state each round.
**Invariant:** every arm ends in exactly one `SetReservation` and the manager's totals are re-verified; the expensive optimizer runs ONLY for genuinely huge operators — small operators take the O(1) bounds path.
**Probe:** `grep -c 'We overshot' src/storage/temporary_memory_manager.cpp` → `1`; `grep -n 'remaining_size > memory_limit ? ComputeReservation' src/storage/temporary_memory_manager.cpp` → :160; `grep -c 'OPTIMIZATION_ITERATIONS_MULTIPLIER = 5' src/storage/temporary_memory_manager.cpp` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "TemporaryMemoryManager UpdateState ComputeReservation DefaultMinimumReservation", limit: 10 });
```

## Verdict
Adopt the ordered ladder (zero → forced-min → no-offload → overshoot → bounded/optimized); adapt ratios to your engine; omit the derivative machinery unless you must arbitrate many big spilling operators fairly.
