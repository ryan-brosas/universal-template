<!-- capsule-v2 -->
# Three-tier link cache — how do you shield a hot redirect path from Redis load and what EXACTLY happens at each tier boundary?

**Source:** dub AGPL-3.0-or-later `main@873edc5a`; Codebase Memory `dub`. **Question:** What are the tiers, their TTLs, their fallback triggers (miss vs ERROR), and the read/write key-derivation asymmetry a porter would silently break?

## LinkCache LRU → Redis → Vercel cache → MySQL
**Path/Symbol:** `apps/web/lib/api/links/cache.ts:LinkCache` (32-97): `get` (71-133), `set` (50-69), `mset` (33-48), `deleteMany` (141+), `_createKey` (91-97); consumers `lib/middleware/link.ts:86`, `propagate-bulk-link-changes.ts`.
**Signature:** `get({domain,key}) → RedisLinkProps | null` (throws only on tier-failure ∧ DB-miss); `mset(links)` / `deleteMany(links)` pipelined.
**Data Shape:** L1 in-process `LRUCache` max 10,000 / ttl 5s; L2 Redis `linkcache:<domain>:<key>` ex 24h; L3 Vercel runtime cache (`getCache()`) ttl 5min — reached ONLY on Redis error; source of truth MySQL via `getLinkViaEdge`.

### Decisive source
```ts
async get({ domain, key }) {
  // NOTE: deliberately NOT this._createKey({domain,key}) — see invariant below
  const cacheKey = `linkcache:${domain}:${key}`;
  let cachedLink = linkLRUCache.get(cacheKey) || null;
  if (cachedLink) { linkLRUCache.set(cacheKey, cachedLink); return cachedLink; }  // refresh
  try {
    cachedLink = await redisGlobalWithTimeout.get<RedisLinkProps>(cacheKey);
    if (cachedLink) { linkLRUCache.set(cacheKey, cachedLink); return cachedLink; }
    return null;                                   // Redis MISS → caller goes to MySQL
  } catch (error) {                                 // Redis ERROR ≠ miss
    cachedLink = (await vercelCache.get(cacheKey)) as RedisLinkProps | null;
    if (cachedLink) return cachedLink;
    const linkData = await getLinkViaEdge({ domain, key });
    if (!linkData) {
      // don't rewrite to /${domain}/notfound since it's expensive (Redis down!)
      throw new Error("Link not found.");
    }
    cachedLink = formatRedisLink(linkData);
    linkLRUCache.set(cacheKey, cachedLink);
    waitUntil(vercelCache.set(cacheKey, cachedLink, { ttl: VERCEL_CACHE_EXPIRATION }));
    return cachedLink;
  }
}
_createKey({ domain, key }) {
  const caseSensitive = isCaseSensitiveDomain(domain);
  const originalKey = caseSensitive ? decodeKey(key) : key;
  const cacheKey = `linkcache:${domain}:${originalKey}`;
  return caseSensitive ? cacheKey : cacheKey.toLowerCase();
}
```

**Flow:** read walks L1→L2, returns null on clean miss (the middleware then fetches MySQL and `waitUntil`s `set`); on Redis FAILURE it detours through L3 before MySQL and backfills LRU+L3. Writes go L1-immediate + Redis + CDN tag revalidation (`static:<domain>:<key>`); bulk paths use pipelines (`mset`, `deleteMany`); `expireMany` soft-invalidates with 1-second TTLs instead of deletes.
**Invariant:** MISS and ERROR are different control flows — a miss short-circuits to null, an error unlocks tier 3; conflating them loses the degradation ladder. Read keys are NOT derived by `_createKey` (which decodes punycode/case-sensitive keys and would double-decode an already-normalized request key); write keys ARE — the asymmetric derivation is pinned by the in-source comment. LRU refresh-on-hit resets recency without extending the 5s TTL semantics. During a Redis outage, a missing link THROWS instead of serving the notfound rewrite, because every request would otherwise pay the expensive page render.
**Probe:** no upstream unit test (coverage caveat). Deterministic probe: mock Redis throwing → get must consult vercelCache then MySQL; mock Redis returning null → must NOT touch vercelCache.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "linkCache linkLRUCache vercelCache formatRedisLink", limit: 10 });
```

## Verdict
Adopt: tiered read path with error-gated fallback tiers, pipeline bulk writes, tag-based CDN revalidation, and the throw-don't-render guard under infra failure. Adapt transports (any LRU/Redis/CDN trio works) and TTLs to your scale. Omit the case-sensitive-domain key dance if your keys normalize uniformly — but keep SOME single canonical key function per direction.
