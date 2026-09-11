<!-- capsule-v2 -->
# Redis Bull jobs service — how does the distributed enqueue path keep meta rows and queue state coherent while primaries stay paused?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the distributed enqueue path keep meta rows and queue state coherent while primaries stay paused?

## Bull add() with primary/worker split
**Path/Symbol:** `packages/nocodb/src/modules/jobs/redis/jobs.service.ts:JobsService.add/onModuleInit/toggleQueue` (27-147).
**Signature:** `add(name: string, data: any, options?: JobOptions): Promise<Job>`; `toggleQueue(): Promise<void>`; `onModuleInit(): Promise<void>`.
**Data Shape:** input `{name, data:{context?, user?, ...}}`; context defaults to `{workspace_id: ROOT, base_id: ROOT}` spread under caller overrides; output Bull Job whose id equals an `nc_jobs` row id (or nanoid for SKIP_STORING_JOB_META types).

### Decisive source
```ts
async onModuleInit() {
    if (process.env.NC_WORKER_CONTAINER === 'false') {
      await this.jobsQueue.pause(true);          // local concurrency flag
    }
    await this.toggleQueue();
    JobsRedis.workerCallbacks[InstanceCommands.RESUME_LOCAL] = async () => {
      await this.jobsQueue.resume(true);
    };
    ...
}
async toggleQueue() {
    // only when NC_WORKER_CONTAINER is neither 'true' nor 'false'
    const workerCount = await JobsRedis.workerCount();
    const localWorkerPaused = await this.jobsQueue.isPaused(true);
    if (workerCount === 0 && localWorkerPaused)   await this.jobsQueue.resume(true);
    else if (workerCount > 0 && !localWorkerPaused) await this.jobsQueue.pause(true);
}
// add(): circular-safe serialize → upsert nc_jobs WAITING row → stamp version → enqueue
data = JSON.parse(JSON.stringify(data, getTrueCircularReplacer()));
...
if (existingJob.status !== JobStatus.WAITING) {
  await Job.update(context, existingJob.id, { status: JobStatus.WAITING });
}
...
await this.jobsQueue.add(data, { jobId: jobData.id, removeOnFail: 1000, ...options });
```

**Flow:** every `add()` first re-evaluates `toggleQueue()` (so a dying worker fleet revives the primary), then serializes payload, then resolves/creates the `nc_jobs` meta row (explicit jobId → reuse-or-reset-to-WAITING; SKIP_STORING_JOB_META → nanoid id only), stamps `_jobVersion`, and enqueues into Bull with `removeOnFail: 1000`.
**Invariant:** the meta-row id and the Bull job id are ALWAYS the same value (`jobId: jobData.id`) — status polling joins the two worlds on that id. A reused jobId whose old run finished must be reset to WAITING before the new Bull job runs, or the UI polls a stale terminal state. The primary's own queue stays PAUSED whenever any dedicated worker exists; it resumes itself only when `workerCount()===0` (worker died) — checked lazily on every add, not via heartbeats.
**Probe:** no unit test exists upstream. Source-grounded probe: `jobs.service.ts:58-75` — exactly one resume branch and one pause branch keyed on `(workerCount===0, isPaused)`; `:140-144` — Bull options always carry `jobId: jobData.id`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsService toggleQueue add bull queue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the lazy primary-resume check on every enqueue, the meta-row/Bull shared id contract, and removeOnFail ring buffer; adapt env names (NC_WORKER_CONTAINER), meta table, and root-scope defaults to host; omit EE-only commands (ASSIGN_WORKER_GROUP etc.) unless porting multi-worker-group routing. Coverage caveat: no in-repo tests; claims are source-grounded.
