<!-- capsule-v2 -->
# Stats dashboard server — aggregator routes + identity-first port reuse

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/stats/src/server.ts`, `port-conflict.ts`. **Question:** How does a local dashboard serve pure projections, and how can two instances share one port without ever killing a foreign process?

## Server face: read projections plus one explicit sync route
**Path/Symbol:** `server.ts:handleApi` (196), `formatStatsDashboardUrl` (311), `startServer` (369); readers from `./aggregator`, `getGainDashboardStats` from `./gain-aggregator`.
**Signature:** `handleApi(req): Promise<Response>`; `startServer(port = 3847, hostname = STATS_DASHBOARD_HOSTNAME): Promise<{ hostname, port, stop }>`.
**Data Shape:** source builds use `CLIENT_DIR`/`STATIC_DIR`; `decodeEmbeddedClientArchive(embeddedClientArchiveTxt)` provides the embedded archive. `IS_PREBUILT` covers compiled or bundled runs; `USE_EMBEDDED_CLIENT` is true whenever that archive exists or a prebuilt runtime requires it.

### Decisive source
```ts
if (path === "/api/stats/providers") return Response.json(await getProviderDashboardStats(range));
if (path === "/api/stats/gain") return Response.json(await getGainDashboardStats(range, project));
if (path === "/api/sync") {
  const result = await syncAllSessions();
  const count = await getTotalMessageCount();
  return Response.json({ ...result, totalMessages: count });
}
```

**Flow:** stats/overview/model/cost/behavior/tool/provider/request/error/gain routes are projections over their aggregators. `/api/sync` is deliberately different: it performs the expensive session scan before returning its count. Static assets come from the embedded archive when available/prebuilt; otherwise `ensureClientBuild` maintains the source-build client.

**Invariant:** ordinary dashboard reads NEVER trigger session ingestion — only `/api/sync` does. Every response carries the identity + requested-host headers, including errors and `OPTIONS`.

**Probe:** `test/server-port-conflict.test.ts` starts the dashboard and verifies headers, bind scope, reuse, reclamation, and refusal to stop foreign listeners; `test/errors-route-range.test.tsx` covers error-route ranges.

## Port conflict: reuse a verified dashboard, reclaim only a verified owner
**Path/Symbol:** `port-conflict.ts:STATS_PROBE_TIMEOUT_MS = 500` (7), `STATS_DASHBOARD_HEADER` (19), `probeStatsDashboard` (31), `reclaimStatsPort` (221), `prepareStatsPort` (256–262), `recoverStatsPort` (265–268); constants `STATS_DASHBOARD_HOSTNAME_HEADER`, `STATS_DASHBOARD_SECURITY_VERSION`.
**Signature:** `prepareStatsPort(port, hostname?): Promise<"retry" | "reuse">`; `recoverStatsPort(port, hostname?): Promise<"retry" | "reuse">`.
**Data Shape:** probe state `"reusable" | "occupied" | "unreachable"`; holders carry `{ pid, image, commandLine }`; runtime-image allowlist `{ bun, node, omp, "omp-stats" }`.

### Decisive source
```ts
const reusable = response.status === 200 &&
  response.headers.get(STATS_DASHBOARD_HEADER) === STATS_DASHBOARD_SECURITY_VERSION &&
  response.headers.get(STATS_DASHBOARD_HOSTNAME_HEADER) === hostname &&
  !response.headers.has("Access-Control-Allow-Origin");
if (probe === "reusable") return "reuse";
if (probe === "occupied") return reclaimStatsPort(port);
return "retry";
```

**Flow:** `startServer` preflights a nonzero port. A correctly stamped, same-host, no-CORS dashboard is REUSED; an occupied or post-bind-conflict port is examined for a known OMP stats owner. `reclaimStatsPort` refuses to stop a foreign process but terminates a verified stats listener and returns `retry` so the same port binds again.

**Invariant:** a port number alone is never identity — reuse requires matching security version AND requested host; reclamation additionally requires a recognizable stats process, so a foreign 200 responder stays running.

**Probe:** `test/server-port-conflict.test.ts` asserts reusable, legacy-reclaim, unresponsive-owner, and foreign-listener cases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(handleApi|startServer|probeStatsDashboard|prepareStatsPort|recoverStatsPort|reclaimStatsPort)$", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt projection-only routes with a single explicit ingest endpoint, stamped identity headers on every response, and probe-verify-before-reuse / process-verify-before-reclaim port handling; adapt header names, security versions, and the runtime-image allowlist to host; omit the embedded-client build plumbing if the host has no compiled-binary story.
