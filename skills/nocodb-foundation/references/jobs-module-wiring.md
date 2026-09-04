<!-- capsule-v2 -->
# Jobs module wiring — how do the CE fallback and EE Redis queue implementations swap behind one interface, and which processors register where?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How is the JobsService token bound per deployment mode, and what must a new processor touch?

## DI token swap + processor registration
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs.module.ts:JobsModuleMetadata` (whole); `jobs-service.interface.ts:IJobsService`.
**Signature:** `{provide: 'JobsService', useClass: FallbackJobsService}` — the Redis `redis/jobs.service.ts:JobsService` is the EE override of the same token; `IJobsService` = `{add, jobStatus, jobList, setJobResult, resumeQueue, pauseQueue, ...}`.
**Data Shape:** providers list = JobsMap + JobsEventService + queue service + 'JobsService' binding + one provider class per processor + 17 migration-job providers; exports `['JobsService', JobsLogService, DuplicateProcessor]`.

### Decisive source
```ts
// CE ships the fallback (in-process PQueue) implementation:
{
  provide: 'JobsService',
  useClass: FallbackJobsService,
},
// processors are plain @Injectable classes; each job type resolves its fn via JobsMap
providers: [
  ..., AtImportProcessor, MetaSyncProcessor, SourceCreateProcessor,
  SourceDeleteProcessor, WebhookHandlerProcessor, DataExportProcessor,
  DataExportCleanUpProcessor, ThumbnailGeneratorProcessor,
  AttachmentCleanUpProcessor, AttachmentUrlUploadProcessor, DataImportProcessor,
],
exports: ['JobsService', JobsLogService, DuplicateProcessor],
```

**Flow:** consumers inject `'JobsService'` and call `add(jobName, data)` — identical for both backends. Processors never talk to Bull directly; they receive typed `job.data` and services by constructor injection. The jobs-map service binds `JobTypes.X → ProcessorClass.job` so the worker admission gate (pass-1 `jobs-processor.md`) can resolve registered functions.
**Invariant:** every new job type touches exactly four places: enum entry (`interface/Jobs.ts`), processor class, module providers list, and the jobs-map registration. The interface is the ONLY contract between enqueue site and execution backend — code that reaches into `queue.add` directly breaks the CE/EE swap. DuplicateProcessor is exported because controllers outside the module drive it.
**Probe:** no unit test upstream. Source-grounded probe: `jobs.module.ts:96-101` — single-token binding; grep shows no processor imports from 'bull' except type-only `Job<T>`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsModuleMetadata FallbackJobsService IJobsService provide JobsService", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single DI-token backend swap and processor-as-plain-class pattern; adapt to your DI container; omit NestJS forwardRef specifics. Coverage caveat: no in-repo tests; source-grounded.
