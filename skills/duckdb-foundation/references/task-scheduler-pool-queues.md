<!-- capsule-v2 -->
# TaskScheduler — how do you run a fixed worker pool over N task queues without losing wakeups?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How does DuckDB's central scheduler let producers enqueue work and workers block for it, across multiple queue types, without missed signals?

## Scheduler owns pools + queues; REGULAR pool drains every queue
**Path/Symbol:** `src/parallel/task_scheduler.cpp:TaskScheduler::TaskScheduler` (:30-35), `ExecuteForever` (:159-213), `TryDequeueAndProcessTask` (:123-157), `SignalForTaskType` (:347-353).
**Signature:** `TaskScheduler::TaskScheduler(DatabaseInstance &db)`; `void ExecuteForever(atomic<bool> *marker, TaskSchedulerType pool_type)`; `bool TryDequeueAndProcessTask(const DBConfig &config, TaskSchedulerQueue &queue, shared_ptr<Task> &task)`.
**Data Shape:** `pools[TASK_SCHEDULER_TYPE_COUNT]` (one `TaskSchedulerPool` per type) + parallel `queues[...]` array; tasks are `shared_ptr<Task>`; each type is REGULAR or ASYNC.

### Decisive source
```cpp
// :30 — one pool + one queue per scheduler type
for (uint8_t i = 0; i < TASK_SCHEDULER_TYPE_COUNT; i++) {
    pools[i]  = make_uniq<TaskSchedulerPool>(db, static_cast<TaskSchedulerType>(i));
    queues[i] = make_uniq<TaskSchedulerQueue>(static_cast<TaskSchedulerType>(i));
}
// :193 — only the REGULAR pool drains ALL queues
if (pool_type == TaskSchedulerType::REGULAR) {
    for (auto &queue : queues) {
        if (TryDequeueAndProcessTask(config, *queue, task)) break;
    }
} else {
    TryDequeueAndProcessTask(config, GetQueue(pool_type), task);
}
```

**Flow:** producer calls `ScheduleTask(token, task, type)` → queue.Enqueue + `SignalForTaskType(type, n)` → idle worker wakes from `pool.Wait()` → dequeues → `task->Execute(mode)` → FINISHED/ERROR drop the task; NOT_FINISHED re-enqueues to the SAME queue + signals again; BLOCKED calls `task->Deschedule()` and drops.
**Invariant:** ASYNC threads only service their own queue; REGULAR threads scan every queue in order. A signal must be emitted after EVERY enqueue that could find the pool idle (`SignalForTaskType(queue.GetPoolType(), 1)` also fires on dequeue failure when `queue.GetTasksInQueue() > 0`, :152-155) — dropping it wedges the pipeline until the next unrelated task.
**Probe:** `grep -c 'for (auto &queue : queues)' src/parallel/task_scheduler.cpp` → `4`; `sed -n '193,202p' src/parallel/task_scheduler.cpp` shows the REGULAR-drains-all / type-specific split.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "TaskScheduler ExecuteForever SignalForTaskType TryDequeueAndProcessTask", limit: 10 });
```

## Verdict
Adopt the two-array pool/queue split and the "REGULAR drains everything" rule plus the re-signal-after-empty-dequeue; adapt pool types to your host's executor categories; omit the jemalloc-derived CPU-id fallbacks inside `GetEstimatedCPUId`.
