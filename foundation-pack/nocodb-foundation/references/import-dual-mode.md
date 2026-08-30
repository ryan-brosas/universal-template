<!-- capsule-v2 -->
# Import run() dual mode — why is the import core a public method separate from job(), and when does the same code path run synchronously?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does one implementation serve both queued and synchronous imports with honest results?

## job() wraps run() with an injectable logger
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/data-import.processor.ts:DataImportProcessor.job/run` (160-329).
**Signature:** `job(job): Promise<result>` → `this.run(job.data, log)`; `run(data: Omit<DataImportJobData,'jobName'>, log = () => undefined, opts?): Promise<{rowsInserted, rowsFailed, linksCreated, valuesUnmatched, linksFailed, sheets}>`.
**Data Shape:** synthetic NcRequest built inside run (`user: {id, email}`, `clientIp`, `ncBaseId/ncSourceId`, `ncParentAuditId`) so audit rows attribute correctly regardless of entry path.

### Decisive source
```ts
/**
 * Core import — runnable without a queue. The Bull `job()` wraps this with a
 * job-bound logger; the AI chat import tool calls it directly for a SYNCHRONOUS
 * import, so it can return real row counts to the user instead of "started".
 */
async run(
  data: Omit<DataImportJobData, 'jobName'>,
  log: (msg: string, verbose?: boolean) => void = () => undefined,
  opts: { cleanupAttachment?: boolean } = {},
) { ... }
```

**Flow:** queue callers get progress lines through JobsLogService; direct callers pass their own logger (or none) and receive typed per-sheet results synchronously. Audit insertion, error-safe message wrapping (NcBaseErrorv2 messages are user-safe; others become generic), and attachment cleanup behave identically in both modes.
**Invariant:** the default logger MUST be a no-op function — any code path assuming console/job-log presence breaks silent sync runs. Error sanitization happens at this boundary: only SDK-typed errors expose real messages to users; infra errors collapse to a fixed string while preserving stack + partial `sheets` results on `err.data`.
**Probe:** no unit test upstream. Source-grounded probe: `data-import.processor.ts:169-178` — doc comment naming the synchronous caller; `:302-319` — safeMessage branch on `instanceof NcBaseErrorv2`.

## Get surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DataImportProcessor run job synchronous import", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt core-method-plus-thin-job-wrapper whenever expensive work may be invoked either async or inline; adapt result schema; omit the AI-chat caller specifics. Coverage caveat: no in-repo tests; source-grounded.
