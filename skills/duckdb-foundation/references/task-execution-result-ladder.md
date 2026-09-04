<!-- capsule-v2 -->
# Task result ladder — what must a worker do with each of the four task outcomes?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** How are TASK_FINISHED / TASK_ERROR / TASK_NOT_FINISHED / TASK_BLOCKED handled so a resumable task is neither lost nor double-run?

## Four-outcome switch; PROCESS_ALL forbids NOT_FINISHED
**Path/Symbol:** `src/parallel/task_scheduler.cpp:TryDequeueAndProcessTask` (:123-157) and `ExecuteTasks` (:215-275).
**Signature:** `TaskExecutionResult Task::Execute(TaskExecutionMode mode)` with mode ∈ {PROCESS_ALL, PROCESS_PARTIAL}; `process_mode = SchedulerProcessPartialSetting ? PROCESS_PARTIAL : PROCESS_ALL` (:126-129).
**Data Shape:** `shared_ptr<Task>` holds `token` (its producer) — used to re-enqueue into the right queue.

### Decisive source
```cpp
switch (execute_result) {
case TaskExecutionResult::TASK_FINISHED:
case TaskExecutionResult::TASK_ERROR:
    task.reset(); break;
case TaskExecutionResult::TASK_NOT_FINISHED: {
    auto &token = *task->token;                 // re-enqueue via the task's OWN producer
    queue.Enqueue(token, std::move(task));
    SignalForTaskType(queue.GetPoolType(), 1);  // signal: someone may be waiting on it
    break;
}
case TaskExecutionResult::TASK_BLOCKED:
    task->Deschedule();                          // task arranges its own continuation
    task.reset(); break;
}
// In ExecuteTasks (PROCESS_ALL): NOT_FINISHED throws InternalException
```

**Flow:** execute → classify → terminal outcomes drop the shared_ptr (reservations release); partial outcome loops the task back through its producer token with a fresh signal; blocked outcome hands control to the event/dependency machinery via Deschedule.
**Invariant:** NOT_FINISHED is only legal in PROCESS_PARTIAL mode — in PROCESS_ALL it's an InternalException (:232-233, :261-262); a re-enqueued task MUST re-signal or an idle pool never notices it.
**Probe:** `grep -c 'TASK_NOT_FINISHED' src/parallel/task_scheduler.cpp` → `3` (one switch arm + two InternalException throws); `grep -c 'SignalForTaskType(queue.GetPoolType(), 1)' src/parallel/task_scheduler.cpp` → `2`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "Task Execute TaskExecutionResult TASK_NOT_FINISHED TASK_BLOCKED Deschedule", limit: 10 });
```

## Verdict
Adopt the outcome→action mapping and the "re-enqueue through the task's own producer + re-signal" pair; adapt the enum names to your executor; omit DuckDB's specific partial-processing setting plumbing.
