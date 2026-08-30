<!-- capsule-v2 -->
# Client response cache — how do you cache list/read responses across a shared store without leaking between servers or principals, and without caching a stale aggregate over a fresh invalidation?

**Source:** typescript-sdk MIT `main@cc4b4161`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** What is the correct partitioning, eviction-race guard, and freshness posture for a client-side response cache driven by server TTL hints?

## Connected graph-selected seam
**Path/Symbol:** `packages/client/src/client/responseCache.ts`: `ClientResponseCache` (:268+), `_partitionFor` (:405-409), `_probe` two-probe lookup (:411-424), `evict` (:426-438), `evictKey` (:446-477), `captureGeneration` (:479-486), `write` generation-guarded (:522-562), `read` (:564-584), `resetForReconnect` (:593-601), `MAX_CACHE_TTL_MS = 86_400_000` (:253).
**Signature:** `write(method, value, capturedGen, freshness?: {expiresAt, scope:'public'|'private', params?})`; store = dumb keyed-value carrier (`get/set/delete/clear`) persisting the JSON string verbatim — every freshness/scope/invalidation decision lives in the cache.
**Data Shape:** Partition encoding = `JSON.stringify([serverIdentity, principal])`; `'public'` scope → `[serverIdentity,'']`, `'private'` → `[serverIdentity, cachePartition]`. JSON escaping makes it collision-free BY CONSTRUCTION: a malicious server cannot craft a `serverInfo.name` whose characters bleed into another namespace. Generation map keyed by `` `${method}\0${params}` ``.

### Decisive source
```ts
// The generation bump is unconditional and FIRST — the write race guard
// relies on the bump, not on the store's deletes completing.
async evict(method) { this._evictionGeneration.set(method, … + 1); await this._deleteBoth(method,''); }
async write(method, value, capturedGen, freshness?) {
    if ((this._evictionGeneration.get(genKey(method, params)) ?? 0) !== capturedGen) return;  // stale-write suppression
    // After storing under the derived partition, delete the OPPOSITE partition:
    // a server flipping cacheScope would otherwise leave a stale entry shadowing
    // the fresh one (own-partition probe order).
}
```

**Flow:** captureGeneration BEFORE page 1 → serve fresh entries under `'use'` mode → fetch → write with freshness `{expiresAt = now + clamp(ttlMs,0..24h), scope}` (missing ttlMs → default; explicit 0 honored as immediately-stale-but-stored for schema retention; missing scope ⇒ private — 'public' too strong to infer) → `list_changed`/`resources/updated` bump generation then delete both partitions → in-flight walk's terminal write observes the bump and skips (result still returns to caller, just not cached).

**Invariant:** evictKey bumps ONLY keys already recorded by captureGeneration — a server streaming updates for never-read URIs cannot grow the map unboundedly. Two-probe read checks own partition first and gates the shared hit on `entry.scope === 'public'` (a co-tenant that omitted its partition writes private bodies at the public slot — scope gate is defence-in-depth). Corrupt-but-fresh external entries are deleted-on-read (else they re-report until expiry). Custom-store failures route to an error sink and resolve — cache bookkeeping never costs the caller its result. resetForReconnect clears only instance-owned stores; user-supplied stores keep their data but lose derived indices/generation map (connection-scoped).

**Probe:** `packages/client/test/client/responseCache.test.ts` (49 tests incl. :475 "auto-aggregate throws ListPaginationExceeded … does not write a partial entry"); substrate pins at :415 describe block; codec round-trip via `responseCacheCodec.test.ts`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "ClientResponseCache evictKey captureGeneration _probe", limit: 10, fields: ["signature", "name", "file"] });
```

**Verdict:** Adopt generation-guarded writes + JSON-encoding partitions + scope-gated two-probe reads for any hint-driven client cache; adapt TTL clamps to your spec; omit the derived tool-index memoization unless you mirror stamp-keyed recompute.
