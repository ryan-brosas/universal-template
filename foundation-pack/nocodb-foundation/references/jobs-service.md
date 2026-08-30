<!-- capsule-v2 -->
# Jobs service — the circular-safe enqueue contract with meta-row upsert

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3`; Codebase Memory `nocodb`. **Question:** How do you enqueue a job so the payload is serializable, the `nc_jobs` meta row is kept consistent, and versioned jobs carry their version?

## Enqueue contract
**Path/Symbol:** `packages/nocodb/src/modules/jobs/fallback/jobs.service.ts:JobsService.add` (23–77); Redis twin `redis/jobs.service.ts:JobsService.add` (77–147).
**Signature:** `async add(name, data, options?: { jobId?, delay? }): Promise<Job>`.
**Data Shape:** `data` may be any object (often with `context`, `user`). `JobVersions` maps `{ [JobTypes.InitMigrationJobs]: 2 }`. `SKIP_STORING_JOB_META` is a list of job types that get no `nc_jobs` row (health-check, use-worker, webhook, workflow jobs, etc.).

### Decisive source
```ts
const context = { workspace_id: RootScopes.ROOT, base_id: RootScopes.ROOT, ...(data?.context||{}) };
data = JSON.parse(JSON.stringify(data, getTrueCircularReplacer()));   // strip cycles
let jobData;
if (options?.jobId) {
  if (SKIP_STORING_JOB_META.includes(name)) jobData = { id: options.jobId };   // no meta row
  else {
    const existing = await Job.get(context, options.jobId);
    if (existing) { jobData = existing; if (existing.status !== WAITING) await Job.update(..., WAITING); }
    else jobData = await Job.insert(context, { id: `${options.jobId}`, job: name, status: WAITING, fk_user_id: data?.user?.id });
  }
}
if (!jobData) {  // no jobId supplied
  if (SKIP_STORING_JOB_META.includes(name)) jobData = { id: await Noco.ncMeta.genNanoid(MetaTable.JOBS) };
  else jobData = await Job.insert(context, { job: name, status: WAITING, fk_user_id: data?.user?.id });
}
data.jobName = name;
if (JobVersions?.[name]) data._jobVersion = JobVersions[name];       // stamp version
return this.fallbackQueueService.add(name, data, { jobId: jobData.id, ...options });
```

**Flow:** normalize context → circular-safe serialize → upsert meta row (or skip for SKIP types) → stamp `jobName` + `_jobVersion` → delegate to the queue's `add`. The fallback and Redis variants are byte-identical in this contract; only the backing queue differs.

**Invariant:** Every enqueued job carries `jobName` (the processor's lookup key) and, when versioned, `_jobVersion` (the processor's admission gate). A jobId that already exists is reset to WAITING, never duplicated. SKIP_STORING_JOB_META jobs get only a nanoid id — no `nc_jobs` row — so the events service must not try to `Job.update` them.

**Probe:** No in-repo unit test exists. Source-grounded probe: the `onModuleInit` enqueues `InitMigrationJobs` (the only versioned job) — trace `add(JobTypes.InitMigrationJobs, {})` and confirm `_jobVersion=2` is stamped.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsService add JobVersions SKIP_STORING_JOB_META", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the circular-safe serialize, the jobId meta-row upsert with WAITING reset, the `_jobVersion` stamping, and the SKIP_STORING_JOB_META fast path; adapt the meta table, id generator, and context shape. Omit the Redis/Bull queue backing unless you need multi-instance. Caveat: no direct test — source-grounded only.
