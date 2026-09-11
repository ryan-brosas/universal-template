<!-- capsule-v2 -->
|# Jobs relay write side — bounded replay ring, refresh-hint pub-sub, and crash-proof finally cleanup

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** The polling capsule mines the read half of `/jobs/listen` — what does the WRITE half guarantee, and how do per-job maps stay leak-free when relays fail?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs.controller.ts:sendJobStatus` (169–292), `sendJobLog` (295–368); read half `listen` (55–166); shutdown companion jobs-listen-shutdown-flush.md.

**Signature:** `@OnEvent(JobEvents.STATUS) sendJobStatus({id, status, data?})`; `@OnEvent(JobEvents.LOG) sendJobLog({id, data:{message}})`. State: `localJobs[jobId] = {messages[], _mid}`, `jobRooms[jobId] = {listeners[]}`, `closedJobs[]`.

**Data Shape:** envelope `{status:'update', data, _mid}` with per-job monotonic `_mid` (starts 1) — the cursor clients echo on reconnect. Message ring capped at 20 (`shift()` beyond). Terminal = COMPLETED|FAILED; REQUEUED non-terminal.

### Decisive source
```ts
} catch (e) {
  // fire-and-forget @OnEvent handler: a thrown/rejected error becomes an
  // unhandledRejection (crashes the process) AND skips the per-job state
  // cleanup below — orphaning localJobs/jobRooms entries on every failure.
  // Under high job-failure churn that is a slow heap leak. Swallow + log.
  this.logger.error(`Failed to relay status for job ${jobId}: ...`);
} finally {
  // Always free per-job in-memory state on a terminal/requeued status, even
  // if an awaited cache/publish above threw.
  if (isRequeued) { delete this.jobRooms[jobId]; delete this.localJobs[jobId]; await NocoCache.del(...).catch(()=>{}); }
  else if (isTerminal) {
    this.closedJobs.push(jobId);
    setTimeout(() => { delete this.jobRooms[jobId]; delete this.localJobs[jobId]; NocoCache.del(...).catch(()=>{}); }, POLLING_INTERVAL * 2).unref();
  }
}
```

**Flow:** event → append envelope to local ring → mirror whole ring to Redis `${scope}:{jobId}:messages` → push to live listeners (headersSent-guarded) → if JobsRedis available publish `{cmd,...data}` so OTHER servers ping their listeners `{status:'refresh'}` (they re-poll; bodies come from cache). Terminal: drop room immediately, tombstone closedJobs after a 1s grace (final message flush), reap tombstones after 2×POLLING_INTERVAL.

**Invariant:** (1) Swallow-and-log is load-bearing in fire-and-forget @OnEvent handlers — an unhandled rejection here kills the process. (2) Cleanup lives in `finally` keyed off the STATUS CLASS computed BEFORE the try: immediate on REQUEUED, delayed one interval×2 on terminal so slow clients fetch last messages. (3) Two-tier storage: local map serves same-process pollers; Redis mirror serves other nodes — pub-sub carries REFRESH HINTS only, never message bodies. (4) `_mid` monotonic across BOTH handlers via the shared localJobs entry.

**Probe:** no unit test upstream. Source-grounded probe: :255-263 (unhandledRejection/heap-leak comment verbatim), :265-268 (finally-cleanup comment), :133-142 (1s grace vs tombstone reap), :207-210+:315-318 (20-cap in both handlers), listen:83-94 (`m._mid > _mid` replay filter).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsController sendJobStatus sendJobLog _mid closedJobs", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt the bounded replay ring with monotonic cursor, hint-only fan-out, and finally-block reaping with terminal-delayed deletes; adapt scopes/cache client; omit JobsRedis for single-instance hosts (local path stands alone). Coverage caveat: no in-repo unit tests; source-grounded.
