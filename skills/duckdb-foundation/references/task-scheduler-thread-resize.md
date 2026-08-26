<!-- capsule-v2 -->
# Thread count reconfiguration — how do you resize a live worker pool safely?

**Source:** DuckDB MIT `main@044a04a7cd39e6e8235f756597ae42dde084e5e5`; Codebase Memory `ext-duckdb`. **Question:** What are the validation and restart rules when `SET threads` changes pool size at runtime?

## total = internal + external; destructor relaunches with force; relaunch under one lock
**Path/Symbol:** `src/parallel/task_scheduler.cpp:SetThreads` (:306-321), `SetAsyncThreads` (:323-331), `RelaunchThreads` (:398-403), `~TaskScheduler` (:37-47).
**Signature:** `void SetThreads(idx_t total_threads, idx_t external_threads)`; `void SetAsyncThreads(idx_t n)`; `void RelaunchThreads()` (takes `thread_lock`, calls `pool->RelaunchThreads(*this, force=false)` per pool).
**Data Shape:** thread counts `idx_t`; `external_threads` are client-supplied threads counted inside the total budget.

### Decisive source
```cpp
if (total_threads == 0) throw SyntaxException("Number of threads must be positive!");
if (total_threads < external_threads)
    throw SyntaxException("Number of threads can't be smaller than number of external threads!");
SetThreadsInternal(TaskSchedulerType::REGULAR, total_threads - external_threads);
// destructor: RelaunchThreads(*this, true) in try/catch — "nothing we can do" if it fails
```

**Flow:** validate → subtract external threads → pool recomputes desired count → `RelaunchThreads()` under the scheduler-wide `thread_lock` spins up/down workers to match.
**Invariant:** validation happens BEFORE any mutation (zero or negative internal counts are rejected atomically); every relaunch path — config change AND destructor — goes through the pools while holding `thread_lock`; the destructor uses force=true and swallows exceptions because throwing from ~dtor is fatal.
**Probe:** `grep -c 'total_threads < external_threads' src/parallel/task_scheduler.cpp` → `1`; `grep -n 'pool->RelaunchThreads(\*this, true)' src/parallel/task_scheduler.cpp` → :41.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-duckdb", query: "SetThreads SetAsyncThreads RelaunchThreads TaskSchedulerPool NumberOfThreads", limit: 10 });
```

## Verdict
Adopt the "validate, then diff-apply under one lock" resizing contract including the forced best-effort shutdown; adapt exception types; omit DuckDB's NO_THREADS compile-mode guards unless you need them.
