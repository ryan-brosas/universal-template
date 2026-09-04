<!-- capsule-v2 -->
|# InitMigrationJobs bootstrap ordering — migrations enqueue last in queue-service init

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** When do versioned migrations actually run relative to queue bring-up — and why does the ordering of init steps matter?

## Path/Symbol
`packages/nocodb/src/modules/jobs/redis/jobs.service.ts:onModuleInit` (24–56; enqueue at :55); fallback twin mirrors; runner `modules/jobs/migration-jobs/init-migration-jobs.ts` (job 142–242).

**Signature:** `onModuleInit(): Promise<void>` — pause-if-primary → toggleQueue → register RESUME/PAUSE_LOCAL worker callbacks → THEN `await this.add(JobTypes.InitMigrationJobs, {})`.

**Data Shape:** empty payload; the runner reads pending migrations itself. Job resolves boolean per the versioned-runner contract (migration-jobs.md).

### Decisive source
```ts
JobsRedis.workerCallbacks[InstanceCommands.RESUME_LOCAL] = async () => {
  this.logger.log('Resuming local queue'); await this.jobsQueue.resume(true);
};
JobsRedis.workerCallbacks[InstanceCommands.PAUSE_LOCAL] = async () => {
  this.logger.log('Pausing local queue'); await this.jobsQueue.pause(true);
};
await this.add(JobTypes.InitMigrationJobs, {});   // LAST line of init
```

**Flow:** module init → primary pauses its local Bull worker when workers exist (redis-jobs-service invariants) → command-bus callbacks registered BEFORE any resume decision → migrations enqueued as the FIRST real work item → admission gates + single-instance lock serialize them.

**Invariant:** (1) Migrations ride the SAME queue as user jobs — they inherit admission, requeue, event fan-out for free; cost: they start only after full queue bring-up. (2) The awaited-in-init enqueue makes migration start deterministic relative to service readiness. (3) Callbacks-before-resume ordering prevents jobs running on a node that should stay paused. (4) Repeat-cron producers (data-export-clean-up) live in the SAME init but are commented out — see repeat-job-registration-gap.md.

**Probe:** no unit test upstream. Source-grounded probe: redis/jobs.service.ts:44-56 verbatim order, fallback twin, pairing capsules migration-jobs.md + redis-jobs-service.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "InitMigrationJobs onModuleInit toggleQueue RESUME_LOCAL", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt migrations-as-first-queue-item with callbacks-before-resume init ordering; adapt boot sequence; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
