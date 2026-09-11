<!-- capsule-v2 -->
# Agent cache LRU — how do you reuse TLS agents across requests without leaking sockets or cross-wiring timelines?

**Source:** bruno MIT `main@675965612ff11b23bc9b6c9541110a287bcb2967`; Codebase Memory `ext-bruno`. **Question:** How does an API client cache http/https Agents by config so repeat requests resume TLS sessions, while keeping per-request debug timelines correct and evicting without socket leaks?

## Connected graph-selected seam
**Path/Symbol:** `packages/bruno-requests/src/utils/agent-cache.ts:getOrCreateAgentInternal` (:230-303), `getAgentCacheKey` (:156), `applySecureContext` (:106), `buildSecureContext` (:77).
**Signature:** `getOrCreateHttpsAgent({ AgentClass, options, proxyUri?, timeline?, disableCache?, hostname? }) → HttpsAgent | HttpAgent`.
**Data Shape:** module-singleton `Map<string, Agent>` (`agentCache`, cap `MAX_AGENT_CACHE_SIZE = 100` :20); cache key = JSON of `{agentClassId, hostname (nulled when proxying), proxyUri, keepAlive, rejectUnauthorized, sha256-16hex hashes of ca/cert/key/pfx/passphrase, minVersion, secureProtocol}`; WeakMaps give each Agent *class* a stable id and memoize timeline wrapper classes.

### Decisive source
```ts
if (!disableCache && agentCache.has(cacheKey)) {
  // Move to end for LRU (delete and re-add)
  const agent = agentCache.get(cacheKey)!;
  agentCache.delete(cacheKey);
  agentCache.set(cacheKey, agent);
  // Update timeline reference for new request
  // The cached agent was created with a previous timeline,
  // but we need events to go to the current request's timeline
  if (timeline && 'timeline' in agent) {
    (agent as any).timeline = timeline;
  }
  ...
```

**Flow:** class id from WeakMap → build compact hashed key → hit ⇒ LRU re-insert + **repoint the cached agent's `.timeline` to the caller's array** + push "Reusing cached https agent" info entry → miss ⇒ wrap class if timeline requested, convert raw `ca` into a `secureContext` (`applySecureContext`: CA-only uses the hash-keyed shared context; pfx/cert/key present builds a combined per-cert context and strips those fields from options), construct with proxy-specific arity (`(proxyUri, options)` vs `(options)`), evict-oldest-then-set.
**Invariant:** eviction must call `.destroy()` on the evicted agent or its pooled sockets leak; `hostname` participates in the key only when NOT proxying (`hostname: proxyUri?.length ? null : hostname`) — dropping that ternary collapses all proxied hosts onto one agent; custom CAs must be ADDED on top of OpenSSL defaults (`tls.createSecureContext()` then `ctx.context.addCACert(cert)`) because passing `ca` to Node REPLACES the default trust store entirely — the single most likely wrong port.
**Probe:** `packages/bruno-requests/src/utils/agent-cache.spec.ts` — pins identical-options reuse, separate agents per rejectUnauthorized/CA/cert/key/pfx/passphrase/proxy/class/keepAlive/hostname, and `updates timeline reference on cached agents`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-bruno", query: "getOrCreateAgentInternal", limit: 5 });
// resolves packages/bruno-requests/src/utils/agent-cache.ts getOrCreateAgentInternal Function :230-303
```

## Verdict
Adopt the keyed-LRU shape, the destroy-on-evict rule, the timeline repoint on hits, and add-on-top secureContext building. Adapt key fields to your client's TLS options; omit Bruno's specific timeline entry strings. Coverage caveat: none — path reports `no_recorded_issue` + `metadata_match` at pin.
