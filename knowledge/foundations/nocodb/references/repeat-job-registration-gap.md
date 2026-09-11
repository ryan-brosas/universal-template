<!-- capsule-v2 -->
|# Repeat-job registration gap — processors can ship registered yet never scheduled

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How do you tell from code alone whether a periodic job actually RUNS — and what's the porting trap?

## Path/Symbol
`packages/nocodb/src/modules/jobs/redis/jobs.service.ts:33-42` (commented producer); twin at `fallback/jobs.service.ts:20-27`; registry side `jobs-map.service.ts:76-78`; dormant processor `data-export-clean-up.processor.ts`.

**Signature:** disabled producer shape: `jobsQueue.add({jobName, context}, {jobId, repeat: {cron: '0 */5 * * *'}})`.

**Data Shape:** both service variants carry the SAME commented block — identical text in redis AND fallback services, the signature of deliberate deprecation (not edition skew or WIP).

### Decisive source
```ts
// await this.jobsQueue.add(
//   {
//     jobName: JobTypes.DataExportCleanUp,
//     context: {},
//   },
//   {
//     jobId: JobTypes.DataExportCleanUp,
//     // run every 5 hours
//     repeat: { cron: '0 */5 * * *' },
//   },
// );
await this.toggleQueue();
```

**Flow:** onModuleInit → (disabled block would register the repeat) → toggleQueue → InitMigrationJobs enqueued. The cleanup processor exists, is DI-registered, is mapped in JobsMap, and WOULD execute if a job arrived — but nothing produces one.

**Invariant:** (1) In Bull-style systems REGISTRATION ≠ SCHEDULING: JobsMap presence proves executability only; producers live in service init blocks. (2) Repeat jobs key on `jobId` for dedupe — re-init upserts rather than duplicates. (3) When porting, audit BOTH directions: every map entry needs a producer audit; every producer needs a map entry. (4) Commented-with-identical-twin = intentional deprecation; commented-in-one-place-only = WIP.

**Probe:** no unit test upstream. Source-grounded probe: redis/jobs.service.ts:33-42 + fallback/jobs.service.ts:20-27 (identical blocks), jobs-map.service.ts:76-78 (live mapping), pairing capsule export-cleanup-job-lifecycle.md (the dormant processor).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "repeat cron DataExportCleanUp jobsQueue add toggleQueue", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the registration-vs-scheduling audit as a porting step; adapt cron expressions; omit the disabled block unless reviving artifact GC in your host. Coverage caveat: no in-repo unit tests; source-grounded.
