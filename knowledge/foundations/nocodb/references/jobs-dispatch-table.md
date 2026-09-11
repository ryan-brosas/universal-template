<!-- capsule-v2 -->
|# JobsMap dispatch table — name→{instance, fn} registry with default method and requeue-on-miss

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How does one queue worker route every job type to its processor without per-type wiring — and why must the map live in an injectable service rather than module scope?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs-map.service.ts:JobsMap._jobMap` (35–95); consumer `modules/jobs/jobs.processor.ts:JobsProcessor.process` (44–110).

**Signature:** `_jobMap(): {[key in JobTypes]?: {this: any; fn?: string}}` exposed via `get jobs()`; `fn` omitted ⇒ caller defaults `'job'`.

**Data Shape:** 15 job types → 10 processor instances. One instance serves many names: DuplicateProcessor ×3 (duplicateBase/Model/Column), MetaSyncProcessor ×2 (default job + metaDiffJob). InitMigrationJobs maps the migration runner.

### Decisive source
```ts
[JobTypes.AtImport]: { this: this.atImportProcessor },            // fn defaults to 'job'
[JobTypes.MetaDiff]: { this: this.metaSyncProcessor, fn: 'metaDiffJob' },
// consumer:
if (!this.jobsMap.jobs[jobName]) { ...requeue... }
const { this: processor, fn = 'job' } = this.jobsMap.jobs[jobName];
if (!processor[fn]) { ...requeue... }
const result = await processor[fn](job);
```

**Flow:** @Process handler receives `{jobName}` → three-gate admission (map hit, method exists, version match) → destructure → invoke under local-concurrency counter + 10-min watchdog. The map is a GETTER so every access re-reads `this.<processor>` — instances are DI-scoped and capturable only after construction, which is why a static/module-level table would break.

**Invariant:** (1) The map binds INSTANCES not classes — processors stay plain @Injectable()s with no queue imports (pairs with jobs-module-wiring's single-token backend swap). (2) Missing name AND missing method both REQUEUE, not throw: deploy races retry instead of failing. (3) New job type = enum value + map entry + processor class; nothing else changes. (4) The `?` optionality means TS won't catch a typo'd key — admission gate 1 is the runtime guard.

**Probe:** no unit test upstream. Source-grounded probe: jobs.processor.ts:49-68 (three gates), :55 (default-method destructure), jobs-map.service.ts:35-40 (fresh-map getter), jobs.module.ts:75 (provider registration).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsMap _jobMap JobTypes DuplicateBase AtImport", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the injectable name→{this, fn} registry with default-method fallback and requeue-on-miss; adapt enum/token names; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
