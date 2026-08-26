<!-- capsule-v2 -->
# Jobs events — status/log fan-out across pub-sub, DB, and in-process emitter

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3`; Codebase Memory `nocodb`. **Question:** How do you keep job status consistent across three surfaces — a pub-sub result channel, the `nc_jobs` DB row, and an in-process EventEmitter — without double-delivering?

## Event fan-out
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs-event.service.ts:JobsEventService` (21–169).
**Signature:** `@OnQueueActive onActive(job)` / `@OnQueueFailed onFailed(job, error)` / `@OnQueueCompleted onCompleted(job, data)`.
**Data Shape:** `SKIP_STORING_JOB_META` (same list as jobs-service). Pub-sub channel: `worker:job:<jobId>`. In-process event: `JobEvents.STATUS` (`job.status`). `awaitingResults` map holds resolve/reject for callers awaiting a job result.

### Decisive source
```ts
@OnQueueFailed()
onFailed(job, error) {
  PubSubRedis.publish(`worker:job:${job.id}`, { success:false, error }).catch(log);
  const emitFailed = () => this.eventEmitter.emit(JobEvents.STATUS, {
    id: job.id.toString(), status: JobStatus.FAILED,
    data: { error: { message: error?.message }, result: error?.data } });
  if (SKIP_STORING_JOB_META.includes(job.data.jobName)) { emitFailed(); return; }  // no DB row
  Job.update({workspace_id:ROOT, base_id:ROOT}, job.id.toString(), { status: FAILED, result: error?.data })
    .catch(log).finally(emitFailed);   // emit only AFTER DB write settles
}
// onCompleted: publish {success:true, result:data};
//   if (data === JobStatus.REQUEUED) { emit STATUS REQUEUED; return; }  // NON-terminal, no DB update
//   else update row COMPLETED + emit.  onActive: publish nothing, update row ACTIVE + emit.
```

**Flow:** Every lifecycle event does three things: (1) publish the result to the pub-sub channel (for cross-instance consumers), (2) update the `nc_jobs` DB row to the terminal/active status (unless SKIP type), (3) emit an in-process `JobEvents.STATUS` event (for the long-poll controller). The DB write settles before the in-process emit (`.finally(emit)`), so listeners never see a status the DB doesn't yet reflect.

**Invariant:** REQUEUED is a *non-terminal* status — it emits but skips the DB update so the row stays WAITING and clients keep polling. Terminal statuses (COMPLETED/FAILED) always reach the DB before the in-process emit. SKIP_STORING_JOB_META jobs never touch the DB (they have no row).

**Probe:** No in-repo unit test exists. Source-grounded probe: `trace_path` on `JobsEventService.onCompleted` resolves `Job.update` (confirmed); the REQUEUED branch is the invariant a porter must preserve.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsEventService onFailed onCompleted REQUEUED", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the three-surface fan-out with DB-before-emit ordering and the non-terminal REQUEUED branch; adapt the pub-sub channel naming, status enum, and meta table. Omit the Redis pub-sub transport if single-process. Caveat: no direct test — source-grounded only.
