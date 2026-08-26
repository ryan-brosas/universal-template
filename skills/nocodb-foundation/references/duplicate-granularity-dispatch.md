<!-- capsule-v2 -->
|# Duplicate processor dispatch — one job type per granularity over a shared service

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How do base/model/column duplication share one pipeline — what does the JOB layer contribute beyond calling the service?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/export-import/duplicate.processor.ts:DuplicateProcessor` (duplicateBase 375–437; initTime at :111); service twin `duplicate.service.ts:DuplicateService.duplicateBase` (26–141); controller `duplicate.controller.ts:123–150`; JobsMap entries `jobs-map.service.ts:42-53`.

**Signature:** three JobTypes (DuplicateBase/DuplicateModel/DuplicateColumn) → `{this: duplicateProcessor, fn: 'duplicateBase'|'duplicateModel'|'duplicateColumn'}`. Processor methods take `Job<{context, baseId?, modelId?, columnId?, options?}>`.

**Data Shape:** controller validates + enqueues + acks `{id, name}` immediately; payload carries entity ids and request context only (rehydrated at execution). The accumulating source→dest idMap threads the whole duplication (see export-idmap).

### Decisive source
```ts
// JobsMap: ALL THREE granularities route to one class via fn names:
[JobTypes.DuplicateBase]:   { this: this.duplicateProcessor, fn: 'duplicateBase' },
[JobTypes.DuplicateModel]:  { this: this.duplicateProcessor, fn: 'duplicateModel' },
[JobTypes.DuplicateColumn]: { this: this.duplicateProcessor, fn: 'duplicateColumn' },
// controller: validate → enqueue → ack fast
const job = await this.jobsService.add(JobTypes.DuplicateBase, { context, ... });
return { id: job.id, name: job.name };
```

**Flow:** REST call → controller guards/validates → enqueue ids-only → processor method per granularity resolves entities and delegates to the shared DuplicateService (serialize-in-dependency-order copy with compensation on failure — duplicate-compensation/duplicate-backfill capsules).

**Invariant:** (1) Granularity lives in the METHOD NAME, not payload flags — three clean entry points, so LOCAL_CONCURRENCY_LIMIT keyed on JobTypes tunes admission per granularity for free. (2) Ids-only payloads are tamper-safe and version-safe. (3) Uniform initTime wrapping (:111) gives every granularity identical timing logs.

**Probe:** no unit test upstream. Source-grounded probe: jobs-map.service.ts:42-53 verbatim, duplicate.controller.ts:123-150 (validate-enqueue-ack), duplicate.processor.ts:375-437 (resolve→delegate), duplicate.service.ts:26-141 (shared pipeline entry).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DuplicateProcessor duplicateBase duplicateModel duplicateColumn jobsService add", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt method-per-granularity routing over flag-switching, ids-only payloads, fast-ack controllers; adapt naming; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
