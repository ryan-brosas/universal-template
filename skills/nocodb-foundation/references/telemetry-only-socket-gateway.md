<!-- capsule-v2 -->
# Telemetry-only socket gateway — how do you expose a WebSocket endpoint that cannot leak data even though auth is optional?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** Why does the gateway swallow JWT failures yet remain safe, and what makes the per-connection id stable?

## Best-effort JWT + hashed attribution id
**Path/Symbol:** `packages/nocodb/src/gateways/socket.gateway.ts:SocketGateway` (whole 96L; namespace built at module scope :19–23).
**Signature:** `onModuleInit(): Promise<void>` wires `server.use(middleware)` + one 'connection' handler; `get io()` accessor.
**Data Shape:** events accepted: 'page' and 'event' only → forwarded verbatim to TelemetryService.sendEvent with `{evt_type, ...args, id}`; id = md5(NC_SERVER_UUID || T.id + handshake.user?.id).

### Decisive source
```ts
// This socket exposes only telemetry beacons (`page`, `event`) — no data
// subscriptions, rooms, or privileged operations are registered below, so an
// unauthenticated connection cannot reach any sensitive surface. The JWT step
// is best-effort attribution only: on success the client's `user` is attached
// to the handshake, and on failure the connection is still accepted so
// anonymous telemetry pings work. This is intentional, not an auth bypass.
try {
  const context = new ExecutionContextHost([socket.handshake as any]);
  const guard = new (AuthGuard('jwt'))(context);
  await guard.canActivate(context);
} catch {}

next();
```
(:51–:65)

**Flow:** module init registers middleware FIRST: run passport jwt guard inside try/catch — success attaches user to the handshake, failure swallowed and connection ACCEPTED (`next()`) → on connect, compute the attribution id by hashing server UUID (+user id when present) so anonymous pings from one server share a stable bucket while identified users differ → only two message handlers exist ('page', 'event'), both forwarding to telemetry; disconnect removes the client and its job slot.
**Invariant:** safety comes from SURFACE MINIMALITY, not authentication — because no rooms/subscriptions/privileged ops are ever registered, accepting unauthenticated connections cannot leak data. If you add any real channel later, this catch-all acceptance becomes an auth bypass. CORS allows origin '*' with credentials:true but allowedHeaders pins ['xc-auth']. Namespace derives from ncSiteUrl's pathname (trailing-slash-normalized) so deployments under sub-paths work without client changes.
**Probe:** `cd packages/nocodb && grep -c "telemetryService.sendEvent" src/gateways/socket.gateway.ts` (=2: page + event) and `grep -c "catch {}" src/gateways/socket.gateway.ts` (=1) and `grep -c "ncSiteUrl" src/gateways/socket.gateway.ts` (=2).
**Direct test:** `src/gateways/socket.gateway.spec.ts` is an EMPTY describe stub ("should be defined") — zero behavioral coverage; grep probes pin the contract.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "SocketGateway telemetryService sendEvent pageview", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt surface-minimality as the security argument + best-effort attribution + hashed stable id; adapt event names to your analytics schema; omit entirely if your product has no anonymous telemetry need. Coverage caveat: spec stub empty; probes are greps.
