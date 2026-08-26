<!-- capsule-v2 -->
# Source delete job — why does base deletion run as a background job at all, and what makes this processor safe to retry?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What does the minimal 28-line delete processor rely on for idempotence?

## delegate-to-service with service-level idempotence
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/source-delete/source-delete.processor.ts:SourceDeleteProcessor.job` (whole, 28 lines).
**Signature:** `job(job: Job): Promise<void>`; payload `{context, sourceId, req}`.
**Data Shape:** no result contract; failures propagate to Bull retry ladder (pass-1 jobs-processor backoff).

### Decisive source
```ts
async job(job: Job) {
  const { context, sourceId, req } = job.data;
  await this.sourcesService.baseDelete(context, { sourceId, req });
}
```

**Flow:** external-source drops can cascade through hundreds of tables and cached models — too slow for a request. The API enqueues; the worker calls the same `baseDelete` used elsewhere. Re-delivery is safe because the service's delete path treats an already-deleted/missing source as a no-op rather than throwing.
**Invariant:** the processor must not pre-check existence then act (TOCTOU) — it delegates the whole decision to the service so a concurrent manual delete between check and execution cannot crash the job. Payload carries the ORIGINAL req (user attribution for audits), not a re-derived user.
**Probe:** no unit test upstream. Source-grounded probe: whole-file delegation at `source-delete.processor.ts:16-27`; contrast with `source-create.processor.ts` where compensation exists precisely because creation is NOT idempotent.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "SourceDeleteProcessor baseDelete sourcesService", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt thin processors whose services are idempotent, making queue retries harmless; adapt audit attribution requirements; omit nothing else — the lesson IS the minimality. Coverage caveat: no in-repo tests; source-grounded.
