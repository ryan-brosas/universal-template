<!-- capsule-v2 -->
# Optimization CPU/IO budget scheduling — how do you admit background compaction into a live write path without starving it or the queries?

**Source:** Qdrant Apache-2.0 `master@74f3e85b`; Codebase Memory `qdrant`. **Question:** Once a plan of merge batches exists, how does the dispatch loop decide whether to start each one, how much resource each gets, and how does it wake itself back up when resources free — without busy-waiting, deadlocking, or getting stuck after a task dies?

## Worker loop: cleanup tick, force-run ladder, IO-permit admission, deduped budget waiter
**Path/Symbol:** `lib/collection/src/update_workers/optimization_worker.rs`: `UpdateWorkers::optimization_worker_fn` (:45-198), `cleanup_optimization_handles` (:208-230), `process_optimization` (:233-265), `launch_optimization` (:270-437), `ensure_appendable_segment_with_capacity` (:445-490), `trigger_optimizers_on_resource_budget` (:493-511). Budget core: `lib/common/common/src/budget.rs`: `ResourceBudget` (:26-239), `ResourcePermit` (:250-403). Production budget built once in `src/main.rs` (:508-511) from `performance.optimizer_cpu_budget` / `optimizer_io_budget`.
**Signature:** `pub async fn optimization_worker_fn(optimizers, sender, receiver, segments, wal, optimization_handles, optimizers_log, total_optimized_points, optimizer_resource_budget, max_handles, has_triggered_optimizers, payload_index_schema, update_operation_lock, update_tracker, optimization_finished_sender)`; `pub fn try_acquire(&self, desired_cpus: usize, desired_io: usize) -> Option<ResourcePermit>`.
**Data Shape:** trigger = `OptimizerSignal::{Operation(op_num), Nop, Stop}` on an mpsc channel (Operation is sent by the update worker after every applied op — pass-2's apply loop); state = a `Vec<StoppableTaskHandle<bool>>` of running optimizations; budget = two tokio semaphores (cpu, io) sized once at startup (`get_cpu_budget` auto ladder: ≤2 CPUs ⇒ 0, 3–32 ⇒ reserve 1, …, >128 ⇒ n/16; `get_io_budget(0, cpu) = cpu`).

### Decisive source
```rust
// optimization_worker.rs :91-102 — a cleanup tick that removed a handle FORCES a re-run
Err(Elapsed { .. }) if cleaned_any => {
    // This branch prevents a race condition where optimizers would get stuck
    // If the optimizer cleanup interval was triggered and we did clean any task we
    // must run optimizers now. ... we might get stuck into yellow state until a new
    // update operation is received. See: <https://github.com/qdrant/qdrant/pull/5111>
    true
}
// :154-172 — admission consumes IO permits only; CPU is taken later inside the build
let desired_cpus = 0;
let desired_io = num_indexing_threads;
if !optimizer_resource_budget.has_budget(desired_cpus, desired_io) {
    let trigger_active = resource_available_trigger.as_ref().is_some_and(|t| !t.is_finished());
    if !trigger_active {
        resource_available_trigger.replace(Self::trigger_optimizers_on_resource_budget(
            optimizer_resource_budget.clone(), desired_cpus, desired_io, sender.clone()));
    }
    let _ = optimization_finished_sender.send(());
    continue;
}
// launch_optimization :328-340 — per-batch permit; if NOTHING started, wake the worker
let Some(mut permit) = optimizer_resource_budget.try_acquire(0, desired_io) else {
    if handles.is_empty() { callback(); }   // else the worker could get stuck
    break;
};
// :349-352 — manual release (the build's IO→CPU swap) wakes the scheduler; drop does NOT
permit.set_on_manual_release(move || { permit_callback(); });
// budget.rs :52-54 — half of what you want is the minimum, so no task starves all others
fn min_cpu_permits(&self, desired_cpus: usize) -> usize {
    desired_cpus.min(self.cpu_budget).div_ceil(2)
}
// budget.rs :380-403 — on_manual_release fires ONLY on explicit release(), never on drop
pub fn release(&mut self, cpu: u32, io: u32) {
    self.release_cpu_count(cpu); self.release_io_count(io);
    if let Some(on_release) = &self.on_manual_release { on_release(); }
}
impl Drop for ResourcePermit {
    fn drop(&mut self) { /* returns permits silently; callback deliberately not called */ }
}
```

**Flow:** recv with a 5 s timeout that doubles as the handle-cleanup tick (finished handles are joined, panics propagated) → decision ladder: Operation ⇒ run; Nop ⇒ run ignoring max_handles; cleanup-tick-that-cleaned ⇒ force-run (PR #5111); cleanup-only ⇒ reloop; Stop/closed ⇒ break → ensure ≥1 appendable segment with capacity (creates a new empty one when all appendables are at/over max_segment_size_kb; failure PANICS the worker — the write path must never lose its landing zone) → manifest backstop sync → max_handles gate (unless forced) → try_recover failed ops → budget gate: no minimum permits ⇒ spawn ONE deduped waiter (`notify_on_budget_available`, exponential backoff to 10 s, then send Nop) and continue → `launch_optimization`: plan once, then per scheduled batch stop at the handle limit, stop if the round's failure latch is set, `try_acquire(0, num_indexing_threads)` (None ⇒ break, callback only if zero handles started), attach the manual-release wake-up, spawn a stoppable task wrapping `optimize` in `catch_unwind` → classify Ok(Ok)/Ok(Cancelled)/Ok(Err)/panic into tracker status, report errors to the holder, set the round's failure latch.
**Invariant:** (1) admission asks for 0 CPU + N IO permits — CPU is acquired later inside the build via `replace_with` (the IO→CPU swap mined in pass-5's build-bake-changes), so the scheduler never blocks a query-serving CPU while a merge is still copying bytes; (2) the minimum-permit rule (`desired.min(budget).div_ceil(2)`) guarantees a waiting task can always make progress once ANY other task releases — no single task can hold enough to starve everyone; (3) exactly one budget-waiter may exist (deduped by `is_finished`), and it wakes via Nop, which bypasses max_handles so a freed budget is never lost behind the handle cap; (4) a finished-handle cleanup MUST re-trigger planning (PR #5111) or the shard sticks in yellow state until the next write; (5) the permit's manual-release callback fires only on explicit `release()` — silent drop must not wake the scheduler, or the IO→CPU swap would double-trigger.
**Probe:** no unit tests exist in `budget.rs` (test gap recorded); the scheduling behavior is pinned by direct reads above plus `lib/collection/src/tests/mod.rs::test_optimization_process` (:54-160, read in pass 5), which asserts the CPU-budget-gated number of concurrent optimization handles and the end-state point count.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "qdrant", query: "launch_optimization try_acquire ResourcePermit notify_on_budget_available min_cpu_permits ensure_appendable_segment_with_capacity", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-semaphore budget with half-desired minimums, the IO-at-admission/CPU-in-build split, the deduped async waiter that re-enters through a max-handles-bypassing signal, the cleanup-tick force-run, and the round-scoped failure latch. Adapt the tokio semaphore/JoinHandle machinery to your host's task system. Omit the Qdrant-specific tracker/telemetry plumbing; keep the panic-catch classification (a panicked optimizer must not kill the worker loop).
