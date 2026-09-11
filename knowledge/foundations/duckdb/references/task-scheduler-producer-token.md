<!-- capsule-v2 -->
# Producer token — how do clients get a private task lane whose count and completion are observable?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does a client thread drive tasks itself (or observe progress) without racing the shared pool?

## ProducerToken spans all queues; per-producer accounting; locked vs requires-lock dequeue
**Path/Symbol:** `src/parallel/task_scheduler.cpp:CreateProducer` (:57-59), `GetTaskFromProducer(Locked)` (:69-81), `GetTaskCountForProducer` (:298-304), `GetProducerCount` (:293-296).
**Signature:** `unique_ptr<ProducerToken> CreateProducer()` (token holds the queues array); `bool GetTaskFromProducer(ProducerToken&, shared_ptr<Task>&)`; `bool GetTaskFromProducerLocked(ProducerToken&, shared_ptr<Task>&) DUCKDB_REQUIRES(token.producer_lock)`.
**Data Shape:** producer lock is an `annotated_mutex`; callers already holding it use the `...Locked` variant (thread-annotation-enforced).

### Decisive source
```cpp
bool TaskScheduler::GetTaskFromProducerLocked(ProducerToken &token, shared_ptr<Task> &task) {
    for (auto &queue : queues) {                  // scan ALL queue types, in order
        if (queue->DequeueFromProducerLocked(token, task)) return true;
    }
    return false;
}
idx_t TaskScheduler::GetProducerCount() const {
    // "We always create a producer in all queues" — read it from REGULAR only
    return GetQueue(TaskSchedulerType::REGULAR).GetProducerCount();
}
```

**Flow:** client creates token → either hands work to the pool or drains its own producer via `WorkOnTasks`-style loops (`Executor::WorkOnTasks` :311, `TaskExecutor::DrainTasks` :62 use exactly these entry points, the latter waiting on `producer_cv` when empty).
**Invariant:** one token = same producer identity in EVERY queue (per-type counts sum across queues); the `DUCKDB_REQUIRES` annotation is the contract that prevents double-locking — never call the Locked variant without holding `token.producer_lock`.
**Probe:** `grep -c 'for (auto &queue : queues)' src/parallel/task_scheduler.cpp` → `4` total loops (:75/:107/:195/:287); `grep -n 'annotated_lock_guard<annotated_mutex> lock(token.producer_lock)' src/parallel/task_scheduler.cpp` → :70.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "ProducerToken GetTaskFromProducer producer_cv DrainTasks", limit: 10 });
```

## Verdict
Adopt the token-per-producer pattern with cross-queue counting and the annotation-split API; adapt to your threading library's lock annotations; omit moodycamel queue internals.
