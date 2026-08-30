<!-- capsule-v2 -->
# Worker pool scheduler — how does a bounded worker pool queue tasks, reuse non-isolated runners, and cancel without zombie workers?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How does the generic `Pool` schedule N tasks over ≤maxWorkers workers, decide when a runner may be reused, and drain everything safely on cancel?

## Recursive-scheduling `Pool`
**Path/Symbol:** `packages/vitest/src/node/pools/pool.ts:Pool` (31–287) — `run` (51–65), `schedule` (67–186), `cancel` (188–216), `getPoolRunner` (222–265), helper `withResolvers` (289–309), `isEqualRunner` (315–328).
**Signature:** `async run(task: PoolTask, method: 'run' | 'collect')`; `private async schedule(): Promise<void>`; `setMaxWorkers(n)`; `WORKER_START_TIMEOUT = 90_000`.
**Data Shape:** `QueuedTask = { task, resolver: withResolvers(), method }`; `ActiveTask extends QueuedTask { cancelTask }`; per-slot `workerIds: Map<1..maxWorkers, boolean>`; `sharedRunners: PoolRunner[]` holds reusable non-isolated runners; `exitPromises` accumulates not-yet-awaited runner terminations.

### Decisive source
```ts
async run(task, method) {
  if (this._isCancelling) {
    throw new Error('[vitest-pool]: Cannot run tasks while pool is cancelling')
  }
  const testFinish = withResolvers()      // every runner failure must reject THIS promise
  this.queue.push({ task, resolver: testFinish, method })
  void this.schedule()
  await testFinish.promise
}

private async schedule(): Promise<void> {
  if (this.queue.length === 0 || this.activeTasks.length >= this.maxWorkers) return
  const { task, resolver, method } = this.queue.shift()!
  try {
    ...acquire slot via getConcurrencyId(); attach onFinished/onTaskError...
    // reuse path — only for non-isolated tasks
    if (!task.isolate && !runner.isTerminated && !isMemoryLimitReached
        && this.queue[0]?.task.isolate === false
        && isEqualRunner(runner, this.queue[0].task)) {
      this.sharedRunners.push(runner)
      return this.schedule()
    }
    if (!runner.isTerminated) {
      this.exitPromises.push(runner.stop({ force: resolver.isRejected })
        .catch(error => this.logger.error(...)))   // terminations started but NOT awaited here
    }
    this.freeWorkerId(poolId)
  }
  catch (error) { return resolver.reject(error) }   // avoid zombie workers when internals fail
  return this.schedule()
}
```

**Flow:** enqueue → fire-and-forget recursive `schedule()` (one loop instance per task; the `activeTasks.length >= maxWorkers` check is the concurrency gate) → on finish, either hand the runner to `sharedRunners` for an immediately-queued compatible task (`isEqualRunner`: same worker type + same project + environment-equal or worker-declared `canReuse`) or start termination in the background → `cancel()` splices the queue and rejects pending resolvers, force-stops actives (second Ctrl-C forces), stops shared runners, then awaits ALL `exitPromises` before clearing `_isCancelling`.

**Invariant:** (1) concurrency is bounded by maxWorkers via the active-task count, never by unbounded Promise.all; (2) isolated tasks NEVER share a runner — sharing requires BOTH sides `isolate:false` plus equality; (3) every scheduling-path error rejects the task's own resolver (no swallowed hang → no zombie worker); (4) cancellation drains queue, actives, shared runners, AND background exits before the flag clears.

**Probe:** `test/e2e/test/cancel-run.test.ts` (:63+) — cancel mid-run asserts running test completes its afterEach, queued tests are skipped with notes; `test/e2e/test/custom-pool.test.ts`, `pool.test.ts`, `pool-worker-exit.test.ts` pin pool behavior incl. worker crash paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "Pool schedule cancel sharedRunners maxWorkers isEqualRunner", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.node.pools.pool.Pool
```

## Verdict
Adopt the resolver-per-task recursive scheduler, the two-sided runner-reuse contract, background-then-await termination, and the cancel drain order. Adapt worker transports (child_process/worker_threads/VM) to the host. Omit the five built-in PoolWorker classes and OTel span wiring unless porting the whole runner layer.
