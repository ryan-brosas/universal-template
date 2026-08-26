<!-- capsule-v2 -->
# Job list visibility window — why does the jobs listing hide results from other users and expire finished rows after an hour?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What is the exact visibility contract of the meta jobs listing endpoint (filters, time window, result redaction)?

## JobsMetaService.list
**Path/Symbol:** `packages/nocodb/src/services/jobs-meta.service.ts:list` (:14-70, whole service 83L).
**Signature:** `async list(context, param: { job?: JobTypes; status?: JobStatus }, req: NcRequest)` → `Job.list(context, { xcCondition })`.
**Data Shape:** xcCondition = optional `{job: eq}` AND optional `{status: eq}` AND one `_or` block: `updated_at > now-1h` OR status ∈ {ACTIVE, WAITING, DELAYED}.

### Decisive source
```ts
/*
 * List jobs for the current base.
 * If the job is not created by the current user, exclude the result.
 * List jobs updated in the last 1 hour or jobs that are still active(, waiting, or delayed).
 */
return Job.list(context, { xcCondition: {...} }).then((jobs) => {
  return jobs.map((job) => {
    if (job.fk_user_id === req.user.id) {
      return job;
    } else {
      const { result, ...rest } = job;
      return rest;                    // other users' jobs: result STRIPPED
    }
  });
});
```

**Flow:** build condition (both user filters optional via spread-ternary) → time/status window: a row survives if it was touched within the hour REGARDLESS of state, or is still live (ACTIVE/WAITING/DELAYED) even if old → per-row ownership check keeps `result` only for the owner.
**Invariant:** The listing never exposes another user's job PAYLOAD (`result`) even though rows are base-visible; terminal jobs (SUCCESS/FAILED) vanish from default listing after 1h — history lives in the nc_jobs table and job-log surfaces mined earlier, not this endpoint. Timestamp comparison goes through `Noco.ncMeta.formatDateTime(dayjs().subtract(1,'hour').toISOString())` — the ncMeta.now string-time discipline (see ncmeta-now-contract), never a raw Date.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `JobsMetaService.list`; grep confirms exactly one result-strip destructure in the file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsMetaService list fk_user_id", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt owner-only payload visibility + recency-or-live listing windows for any shared queue introspection surface. Adapt the window constant and status enum to host. Omit the xcCondition builder shape (SDK-specific).
