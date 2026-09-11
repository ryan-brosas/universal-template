<!-- capsule-v2 -->
# UseWorker env-gated twin — why does the same decorator become a no-op, a PubSub-blocking RPC, or nothing depending on deployment topology?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does @UseWorker differ from @Pollable, and which two environment gates decide its behavior at DECORATION time?

## Decoration-time gating + subscribe-before-enqueue race control
**Path/Symbol:** `packages/nocodb/src/decorators/use-worker.decorator.ts:UseWorker` (:12–:71 whole file 71L).
**Signature:** `UseWorker(): MethodDecorator`; injects token `'JobsService'` (string DI — the CE/EE swap seam); returns a Promise of the remote result (BLOCKING, unlike Pollable's `{id}`).
**Data Shape:** subscribes `worker:job:<jobId>` expecting `{success: boolean; result?; error?}`; payload identical to Pollable (`{service, method, args}`).

### Decisive source
```ts
if (!PubSubRedis.available) return descriptor;          // gate 1: no redis → plain method
if (process.env.NC_WORKER_CONTAINER !== 'false') return descriptor;  // gate 2: not web container → plain
// ...
PubSubRedis.subscribe<...>(`worker:job:${jobId}`, async (data, unsubscribe) => {
  if (data.success) resolve(data.result); else reject(data.error);
  await unsubscribe();
}).then(() => {
  jobService.add(JobTypes.UseWorker, {...}, { jobId }).catch((e) => { logger.error(e); });
}).catch((e) => { logger.error(e); reject(e); });
```
(:16–:55)

**Flow:** BOTH gates evaluate when the DECORATOR runs (class definition time), not per-call — topology is fixed for process lifetime → wrapped fn subscribes FIRST, then enqueues, so the completion event can never arrive before the listener exists → job add failure is logged-not-rethrown inside `.then` but leaves the caller hanging on the promise (subscribe cleanup absent in that path — recorded asymmetry) → success/error resolve/reject then unsubscribe.
**Invariant:** subscribe-before-enqueue ordering is the race guard; gate order matters because `NC_WORKER_CONTAINER !== 'false'` means WORKER containers and redis-less hosts keep the local method (workers must execute, not delegate). Distinct from @Pollable: no `{id}` handshake, no nc_jobs meta row consumer contract — callers await the value directly.
**Probe:** `cd packages/nocodb && grep -n "NC_WORKER_CONTAINER\\|PubSubRedis.available" src/decorators/use-worker.decorator.ts` (:16/:18 exactly one site each) and `grep -n "worker:job:" src/decorators/use-worker.decorator.ts` (:37 single channel template).

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "UseWorker PubSubRedis NC_WORKER_CONTAINER worker:job JobsService", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt decoration-time topology gating + subscribe-first ordering; adapt env var names/pubsub transport; omit entirely if single-container. Coverage caveat: no spec; count-pinned greps.
