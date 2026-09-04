<!-- capsule-v2 -->
# Jobs polling — the long-poll status endpoint with incremental message log

**Source:** NocoDB Sustainable Use License `develop@f7513664f3f3`; Codebase Memory `nocodb`. **Question:** How do you let a client long-poll a job's status/progress over plain HTTP without WebSockets, and clean up per-job state without leaking?

## Long-poll surface
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs.controller.ts:JobsController` (29–369).
**Signature:** `@Post('/jobs/listen') listen(@Res() res, @Req() req, @Body() body: { _mid: number; data: { id } })`; `@OnEvent(JobEvents.STATUS) sendJobStatus(data)`; `@OnEvent(JobEvents.LOG) sendJobLog(data)`.
**Data Shape:** Per-job state: `jobRooms[jobId] = { listeners: Response[] }`, `localJobs[jobId] = { messages: [], _mid }`, `closedJobs[]`. Cache key `JOBS_POLLING:<jobId>:messages`. `POLLING_INTERVAL = 30000`. `nanoidv2` 14-char for `res.resId`.

### Decisive source
```ts
async listen(res, req, body) {
  const { _mid = 0, data } = body; const jobId = data.id;
  res.setHeader('Cache-Control','no-cache, must-revalidate'); res.resId = nanoidv2();
  const messages = this.localJobs[jobId]?.messages ?? (await NocoCache.get('root', `${JOBS_POLLING}:${jobId}:messages`, TYPE_OBJECT))?.messages;
  const newMessages = messages?.filter(m => m._mid > _mid) ?? [];
  if (newMessages.length) { res.send(newMessages); return; }          // replay since last _mid
  if (this.closedJobs.includes(jobId)) { res.send({ status:'close' }); return; }
  if (!this.jobRooms[jobId]) {                                        // first listener -> subscribe
    this.jobRooms[jobId] = { listeners:[res] };
    if (JobsRedis.available) await JobsRedis.subscribe(jobId, async (data) => { /* refresh all, on terminal unsubscribe+delete room */ });
  } else this.jobRooms[jobId].listeners.push(res);
  res.on('close', () => { /* remove res by resId from room */ });
  setTimeout(() => { if (!res.headersSent) res.send({ status:'refresh' }); }, POLLING_INTERVAL).unref();  // 30s keepalive
}
// sendJobStatus: builds {status:'update', data, _mid:++localJobs[jobId]._mid}, pushes to messages (cap 20),
//   writes to cache, sends to all room listeners, publishes to pub-sub; finally:
//   isRequeued -> delete room+localJobs+del cache;  isTerminal -> push closedJobs (expire 60s) + delayed cleanup
```

**Flow:** A client POSTs with its last-seen `_mid`; the server replays any newer cached messages immediately, else holds the response open in a per-job room. Each STATUS/LOG event broadcasts `{status:'update', data, _mid}` to all listeners and appends to a capped (20) message log persisted to cache. A 30s refresh keepalive prevents idle timeouts. On terminal status the job is tombstoned in `closedJobs` for 60s (so late pollers get `close`), then per-job state is freed.

**Invariant:** `_mid` is strictly monotonic per job and drives incremental replay — a client that reconnects with a stale `_mid` gets only the messages it missed. Per-job in-memory state is always freed in a `finally` (even if a cache/pub-sub round-trip throws), preventing a heap leak under high job churn. `res.headersSent` guards every send so a response is never written twice.

**Probe:** No in-repo unit test exists. Source-grounded probe: the `onModuleDestroy` sends `{status:'refresh'}` to all unconsumed listeners on shutdown.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsController listen jobRooms _mid sendJobStatus", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the `_mid` incremental-replay long-poll, the per-job listener rooms, the 30s refresh keepalive, the 60s closed-job tombstone, and the finally-based state cleanup; adapt the cache layer, polling interval, and auth guards. Omit the Redis pub-sub relay if single-process. Caveat: no direct test — source-grounded only.
