<!-- capsule-v2 -->
|# SourceCreate compensation processor — error-in-result triggers delete-then-rethrow with meta-config scrub

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** The job layer behind source-create-compensation — what exactly happens when the service reports failure inside its RESULT, and what gets scrubbed on success?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/source-create/source-create.processor.ts:SourceCreateProcessor.job` (18–49); silent twin `source-delete/source-delete.processor.ts` (16–27).

**Signature:** `job(job: Job<{context, baseId, source, req, user}>)` → destructures `{source: createdSource, error}` from the service RESULT (not an exception). Delete twin: `job(job)` → straight `sourcesService.baseDelete(context, {sourceId, req})`.

**Data Shape:** `logBasic` closure fans every progress line to BOTH the job log stream (`jobsLogService.sendLog(job, {message})`) and debug. Compensating delete synthesizes attribution: `req: {user: user || req.user || {}}`.

### Decisive source
```ts
const { source: createdSource, error } =
  await this.sourcesService.baseCreate(context, { baseId, source, logger: logBasic, req });

if (error) {
  await this.sourcesService.baseDelete(context, {
    sourceId: createdSource.id,
    req: { user: user || req.user || {} },
  });
  throw error;                        // rethrow AFTER compensating
}

if (createdSource.isMeta()) {
  delete createdSource.config;        // never echo meta-db credentials into logs/results
}
```

**Flow:** CREATE → baseCreate streams progress via logBasic → error-in-result ⇒ baseDelete the half-created source THEN throw (queue's failure ladder takes over — no try/catch here) → success scrubs config when the created source IS the meta source. DELETE → pure delegation to the idempotent service with original req attached for attribution; no TOCTOU pre-checks.

**Invariant:** (1) Failure is signaled by RESULT so partial-success state survives to the only layer that knows both what was created and how to name it for deletion. (2) Compensation PRECEDES rethrow — never leave a half-source for a cleanup cron. (3) Meta-source config scrub is secret hygiene at the boundary. (4) Attribution fallback chain guarantees the audit delete always carries an actor. (5) The delete twin's brevity IS the invariant: idempotent service + no pre-checks means duplicate queued deletes converge safely.

**Probe:** no unit test upstream. Source-grounded probe: source-create.processor.ts whole (50 L), source-delete.processor.ts whole (28 L), pairing capsules source-create-compensation.md / source-delete-idempotent.md / jobs-log-fanout.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "SourceCreateProcessor baseCreate baseDelete sendLog SourceDeleteProcessor", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt result-carried errors + compensate-before-rethrow + boundary secret-scrub + pre-check-free idempotent deletion; adapt service names; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
