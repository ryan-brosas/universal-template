<!-- capsule-v2 -->
|# Jobs listen shutdown flush — answering parked long-pollers at module destroy

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** What happens to clients parked in `/jobs/listen` when the process shuts down — the shutdown-ordering seam the polling capsules don't cover?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs.controller.ts:JobsController.onModuleDestroy` (36–45); read half `listen` (55–166); write half `sendJobStatus/sendJobLog` (169–368).

**Signature:** `onModuleDestroy()` — NestJS hook; iterates every job room and answers each unsent response.

**Data Shape:** `jobRooms[jobId].listeners: (Response & {resId?: string})[]` — the same parked HTTP responses the read half holds open.

### Decisive source
```ts
onModuleDestroy() {
  Object.keys(this.jobRooms).forEach((jobId) => {
    const room = this.jobRooms[jobId];
    room.listeners.forEach((res: Response & { resId?: string }) => {
      if (!res.headersSent) {
        res.send({ status: 'refresh' });
      }
    });
  });
}
```

**Flow:** SIGTERM/module teardown → onModuleDestroy runs BEFORE connections are forcibly closed → every parked listener gets one final `{status:'refresh'}` → clients re-poll another instance instead of waiting out a 30s keepalive against a dead socket.

**Invariant:** (1) Shutdown sends REFRESH hints, never fabricated job state — correctness stays with the relay. (2) The `headersSent` guard makes double-sends impossible when a listener was answered in the same tick. (3) Without this hook, rolling deploys strand pollers up to POLLING_INTERVAL (30s) on dead sockets; the fix costs one loop at destroy. (4) No awaits needed: Express drains after headers go out.

**Probe:** no unit test upstream. Source-grounded probe: jobs.controller.ts:36-45 whole method, :53-58 (no-cache + parked res), pairing capsules jobs-polling.md + jobs-relay-write-side.md.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "JobsController onModuleDestroy jobRooms listeners headersSent", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt flush-on-destroy for long-poll surfaces; adapt framework hooks; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
