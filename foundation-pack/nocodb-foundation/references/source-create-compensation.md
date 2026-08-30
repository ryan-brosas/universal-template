<!-- capsule-v2 -->
# Source create compensation — why does a background source-creation job delete what it just created when the post-create step fails?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the processor signal partial failure when the underlying service returns `{source, error}` instead of throwing?

## error-in-result → baseDelete + rethrow
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/source-create/source-create.processor.ts:SourceCreateProcessor.job` (18-49).
**Signature:** `job(job: Job): Promise<void>`; service contract `baseCreate(context, {baseId, source, logger, req}): Promise<{source: Source; error?: any}>`.
**Data Shape:** job data `{context, baseId, source, req, user}`; log closure fans out to JobsLogService + debug.

### Decisive source
```ts
const { source: createdSource, error } =
  await this.sourcesService.baseCreate(context, {
    baseId, source, logger: logBasic, req,
  });

if (error) {
  await this.sourcesService.baseDelete(context, {
    sourceId: createdSource.id,
    req: { user: user || req.user || {} },
  });
  throw error;
}

if (createdSource.isMeta()) {
  delete createdSource.config;      // strip credentials before result serialization
}
```

**Flow:** the long-running external-DB connect/introspect can fail AFTER the Source row exists; the service reports that as `{source, error}` rather than throwing (it needs to return the id for cleanup). The processor then deletes the half-created source and rethrows so Bull marks the job failed and retries run clean.
**Invariant:** cleanup must use the RETURNED source's id even on error — the row exists. The synthetic req for deletion falls back `user || req.user || {}` because audit/user resolution may not survive the failed path. Secrets (`config`) are stripped from meta sources before the result travels back through job-result storage.
**Probe:** no unit test upstream. Source-grounded probe: `source-create.processor.ts:28-46` — destructure-error branch ordering delete→throw→strip-config.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "SourceCreateProcessor baseCreate baseDelete isMeta config", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the compensate-and-rethrow shape for multi-step creations whose first step commits before later steps can fail; adapt service names/audit plumbing; omit the isMeta config-stripping if your results never embed credentials. Coverage caveat: no in-repo tests; source-grounded.
