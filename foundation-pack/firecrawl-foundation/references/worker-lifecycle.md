<!-- capsule-v2 -->
# Worker lifecycle — how do queue workers gate admission on system load and shut down without losing jobs?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I run long-lived job workers that respect RAM/CPU limits, liveness, and graceful SIGTERM?

## Worker lifecycle
**Path/Symbol:** `apps/api/src/services/queue-worker.ts`:`workerFun` (:253-319) + `crawlFinishWorker` (:321-406) + shutdown block (:236-249, :508-515) + liveness endpoint (:408-455).
**Signature:** `workerFun(queue, processJobInternal)` — manual pull loop (NOT BullMQ's auto-run); `processJobInternal(token, job)`; crawl-finish worker polls `crawlFinishedQueue.getJobToProcess()` (nuq) with adaptive backoff.
**Data Shape:** module state: `runningJobs: Set<string>` for in-flight tracking, `isShuttingDown` flag set by SIGINT/SIGTERM handlers, `cantAcceptConnectionCount` with stall threshold 25, lock renewal interval 15s (finish worker) / `JOB_LOCK_EXTEND_INTERVAL` (bullmq workers), no-job backoff 500ms→10s doubling (reset to 500ms on any job).

### Decisive source
```ts
while (true) {
  if (isShuttingDown) break;                       // stop ACCEPTING; in-flight jobs keep running
  const canAcceptConnection = await monitor.acceptConnection();   // RAM/CPU admission control
  if (!canAcceptConnection) {
    cantAcceptConnectionCount++;
    isWorkerStalled = cantAcceptConnectionCount >= 25;
    await sleep(cantAcceptConnectionInterval); continue;
  } else if (!currentLiveness) { await sleep(...); continue; }    // k8s networking check result
  const job = await worker.getNextJob(token);
  if (job) {
    runningJobs.add(job.id);
    processJobInternal(token, job).finally(() => runningJobs.delete(job.id));  // NOT awaited — concurrency
    await sleep(gotJobInterval);
  } else { await sleep(connectionMonitorInterval); }
}
// shutdown tail:
_logger.info("All workers exited. Waiting for all jobs to finish...");
while (runningJobs.size > 0) { await sleep(500); }
process.exit(0);
```

**Flow:** startup initializes the blocklist and engine-forcing tables (exit(1) on blocklist failure), optionally starts monitor schedulers + dedicated consumers ("search checks drain on their own consumer so they can't starve the rest"), then runs three workers concurrently via `Promise.all`. Each job handler owns its own lock-renewal setInterval cleared in `finally`; TransportableErrors are deliberately excluded from Sentry ("they're flow control, not failures"). The liveness HTTP endpoint flips a shared `currentLiveness` boolean that gates ADMISSION (not processing).
**Invariant:** Shutdown ordering is accept-stop → drain-tracked-jobs → exit; a porter who awaits processJobInternal inline serializes all jobs (the `.finally()` un-await is deliberate bounded-by-sleep concurrency). Locks MUST be renewed on an interval shorter than lock duration or long jobs get double-processed after a stalled-check steal.
**Probe:** anchored at repo root `apps/api/src`: `grep -n 'runningJobs.size > 0' services/queue-worker.ts` → exactly 1 hit at :510; `grep -n 'maxStalledCount: ' services/queue-worker.ts` → 1 hit showing 10.
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "workerFun getNextJob runningJobs shutting down", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt admission-controlled pull loops + tracked-in-flight drain + flow-control-error exemption from crash reporting for job workers; adapt intervals/thresholds; omit BullMQ/nuq specifics per your queue.
