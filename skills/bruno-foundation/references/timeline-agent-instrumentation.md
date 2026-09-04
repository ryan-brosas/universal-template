<!-- capsule-v2 -->
# Timeline agent — per-request connection telemetry via subclass wrapping with cached-agent timeline repointing

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How do you instrument TLS/DNS/connection events for every request when agents are cached and shared across concurrent requests?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/utils/timeline-agent.ts:createTimelineAgentClass` (:56-214), `createTimelineHttpAgentClass` (:226+); wrapper-class memoization in `agent-cache.ts` (`timelineClassCache` WeakMaps).
**Signature:** `createTimelineAgentClass(BaseAgentClass) → class TimelineAgent extends BaseAgentClass { constructor(options, timeline?) }`.
**Data Shape:** `TimelineEntry = {timestamp: Date, type: 'info'|'tls'|'error', message}`; agent carries `timeline: TimelineEntry[]`, `alpnProtocols`, `caProvided`, `caCertificatesCount`.

### Decisive source
```ts
createConnection(options: any, callback: any) {
  const { host, port } = options;
  // Capture the current timeline reference to avoid race conditions
  // when multiple concurrent requests reuse the same cached agent
  const timeline = this.timeline;
  const log = (type, message) => { timeline.push({ timestamp: new Date(), type, message }); };
  ...
  try {
    socket = super.createConnection(options, callback);
  } catch (error: any) {
    log('error', `Error creating connection: ${error.message}`);
    error.timeline = timeline;   // errors carry the entries collected so far
    throw error;
  }
```

**Flow:** constructor splits proxy vs direct arity (`options.proxy` ⇒ `super(proxyUri, tlsOptions)`), forces `rejectUnauthorized ?? true` default, strips the non-standard `caCertificatesCount` before super() → createConnection logs ALPN offer + CA counts + `Trying host:port` → socket events append lookup/connect/secureConnect (protocol+cipher suite, accepted ALPN, peer cert) → on failure the thrown error gets `.timeline` attached so callers can still render partial progress.
**Invariant:** the timeline ARRAY is captured LOCALLY at createConnection entry because the cached agent's `.timeline` may be REPOINTED by a newer request mid-flight (see agent-cache-lru capsule) — logging through `this.timeline` would interleave two requests' events; wrapper classes are WeakMap-memoized so repeated `getOrCreateHttpsAgent` calls don't redefine subclasses (and class identity feeds the cache key via id map).
**Probe:** exercised via `agent-cache.spec.ts` "timeline support" section (:136+: uses provided timeline array / updates timeline reference on cached agents / does not add timeline when none provided).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "createTimelineAgentClass createConnection timeline", limit: 5 });
```

## Verdict
Adopt subclass-wrap instrumentation with local-timeline capture and error-carried partial logs. Adapt event vocabulary to your observability plane; omit CA-count presentation. Coverage caveat: pinned indirectly through agent-cache specs, no standalone spec file.
