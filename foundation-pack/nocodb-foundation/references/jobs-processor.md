<!-- capsule-v2 -->
# Jobs processor — the worker admission gate and requeue budget

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3`; Codebase Memory `nocodb`. **Question:** What invariants must a job processor enforce so transient skew (new job type, renamed fn, version bump, local concurrency pressure) never wedges a job in WAITING forever?

## Worker admission
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs.processor.ts:JobsProcessor.process` (46–112) and `.requeue` (114–156).
**Signature:** `@Process({concurrency: NC_WORKER_CONCURRENCY}) process(job: Job<JobData>): Promise<any>`.
**Data Shape:** `JobData = { jobName, _jobAttempt?, _jobVersion?, context, user }`. `NC_WORKER_CONCURRENCY` defaults to 10 via `parseWorkerConcurrency` (min 1). Per-type local caps: `{AtImport:2, ThumbnailGenerator:1, AttachmentUrlUpload:1}` tracked in a module-level `LOCAL_JOB_COUNT_MAP`.

### Decisive source
```ts
// three-gate admission
if (!this.jobsMap.jobs[jobName]) { await this.requeue(job); return; }        // 1: registered name
const { this: processor, fn='job' } = this.jobsMap.jobs[jobName];
if (!processor[fn]) { await this.requeue(job); return; }                     // 2: resolvable fn
if (JobVersions[jobName] || job.data?._jobVersion) {
  if (JobVersions[jobName] !== job.data._jobVersion) { await this.requeue(job); return; } // 3: version
}
const localLimit = LOCAL_CONCURRENCY_LIMIT[jobName];                         // local back-pressure
const localRunning = LOCAL_JOB_COUNT_MAP.get(jobName) ?? 0;
if (localLimit !== undefined && localRunning >= localLimit) { await this.requeue(job); return; }
// long-run watchdog: Timer.start logs every 10 min while still processing
// finally: decrement LOCAL_JOB_COUNT_MAP, stop watchdog

async requeue(job) {
  await job.releaseLock(); await job.remove();          // remove so ids don't clash
  const attempt = job.data?._jobAttempt ?? 1;
  if (attempt > JOB_REQUEUE_LIMIT) {                    // 60
    // surface as FAILED (listeners + nc_jobs row reach terminal state, else row sits WAITING)
    this.jobsEventService.onFailed(job, error); this.telemetryService.sendSystemEvent(...); return;
  }
  await this.jobsEventService.onCompleted(job, JobStatus.REQUEUED);  // non-terminal
  job.data._jobAttempt = attempt + 1;
  return this.jobsService.add(job.data.jobName, job.data, { jobId: job.id.toString(), delay: jobRequeueDelay(attempt) });
}
// jobRequeueDelay(attempt) = min(5000 * 2^(attempt-1), 60000)  // 5s,10s,20s,40s,60s...
```

**Flow:** admit → run (watchdog armed) → return result; any admission miss or local-cap hit → `requeue` (release lock, remove, exponential-delay re-add, bump `_jobAttempt`); budget exhausted → FAILED + telemetry. `JOB_REQUEUE_LIMIT=60`, base delay 5s, max 60s ⇒ ~57 min total budget before drop.

**Invariant:** A requeued job is never left in a non-terminal DB state — the final drop surfaces as FAILED (not silently dropped), and REQUEUED is emitted as a *non-terminal* status so listeners keep polling. The local concurrency cap is per-type and process-local (not Bull's global concurrency).

**Probe:** No in-repo unit test exists. Source-grounded probe: `search_graph` resolves `JobsProcessor.process` with callees `requeue` and `jobRequeueDelay` (confirmed via trace_path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsProcessor requeue jobRequeueDelay", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three-gate admission + exponential-backoff requeue + FAILED-on-budget-exhaustion; adapt the cap table, backoff constants, and telemetry sink. Omit the Bull `@Process` decorator specifics if not on Bull. Caveat: no direct test — source-grounded only.
