<!-- capsule-v2 -->
# Fallback queue — how to build a Bull-compatible in-memory job queue

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3`; Codebase Memory `nocodb`. **Question:** How do you provide a drop-in Bull `Queue`/`Job` API without Redis, so a codebase can run single-process (CE) or distributed (EE) behind one interface?

## Queue core
**Path/Symbol:** `packages/nocodb/src/modules/jobs/fallback/fallback-queue.service.ts:QueueService` (28–294).
**Signature:** `class QueueService { static queue = new PQueue({concurrency:2}); add(name, data, opts?): Job; getJob(id); getJobs(types); removeRepeatable(opts); static reset(); }`.
**Data Shape:** `Job` = `{ id, name, status, data, repeat?, delay?, timestamp?, timeoutRef?, remove?, getState?, moveToCompleted?, moveToFailed? }`. Statuses from `JobStatus` (`waiting/active/delayed/failed/completed/paused/refresh/requeued`). All state is static — one process-global queue shared by every consumer.

### Decisive source
```ts
add(name, data, opts?) {
  const id = opts?.jobId || `${this.queueIndex++}`;
  const existingJob = this.queueMemory.find(q => q.id === id);
  // if existing + repeat -> return existingJob (idempotent)
  // if existing + !waiting -> reset status to WAITING
  const helperFns = (timeoutRef=null) => ({ getState, moveToCompleted, moveToFailed, remove });
  if (opts?.repeat) {
    // parse cron -> setTimeout(delayMs) -> queue.add(jobWrapper(childJob))
    //   .then(() => queue.add(scheduleNextExecution))   // only AFTER completion
    // catch -> queue.add(scheduleNextExecution)         // reschedule despite error
  } else if (opts?.delay) {
    const t = setTimeout(() => this.queue.add(() => this.jobWrapper(job)), opts.delay).unref();
    job.timeoutRef = t; Object.assign(job, helperFns(t));
  } else {
    this.queueMemory.push(job); this.queue.add(() => this.jobWrapper(job));
  }
}
static reset() {           // test isolation
  this.queue.clear();
  for (const j of this.queueMemory) if (j.timeoutRef) { clearTimeout(j.timeoutRef); j.timeoutRef=undefined; }
  this.queueMemory.length = 0; this.queueIdCounter = 1; this.processed = 0;
}
```

**Flow:** `jobWrapper(job)` emits `ACTIVE` → looks up `jobsMap.jobs[name]` (missing ⇒ skip, no event) → `await processor[fn](job)` → emits `COMPLETED` on success / `FAILED` on throw. Emitter listeners in the constructor update `queueMemory` status and forward to `JobsEventService.onActive/onCompleted/onFailed` (with `skipEvent` to avoid double-forward from `moveToCompleted/moveToFailed`).

**Invariant:** `add()` with the same `jobId` is idempotent — it reuses the in-memory job and never duplicates. Recurring jobs reschedule only after the current run completes (no overlapping cron ticks). Delayed jobs keep a tracked `timeoutRef` so `reset()`/`remove()` can cancel still-pending timers (else they fire post-cleanup against a torn-down DB).

**Probe:** No in-repo unit test exists (nocodb package carries only `sqlmigrator.test.ts`). The `reset()` comment documents the leak it prevents: a debounced table-sync resync firing after base teardown. Port with your own test: enqueue a delayed job, call `reset()`, assert the timer never fires.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "QueueService fallback queue add", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the static PQueue + memory-registry pattern, the idempotent-jobId add, the repeat-after-completion rescheduling, and the tracked-timer reset; adapt concurrency (env `NC_FALLBACK_QUEUE_CONCURRENCY`), cron parser, and status enum. Omit the `removeRepeatable` no-op stub unless you need Bull parity. Caveat: no direct test — source-grounded only.
