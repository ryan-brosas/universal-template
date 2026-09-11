<!-- capsule-v2 -->
# Fetch Promise Cache — how do I dedupe concurrent identical fetches without a request-library cache?

**Source:** shadcn-ui UNLICENSED `main@1773ecfeeb4a04366978d353e69b5c7ded78dcb2`; Codebase Memory `shadcn-ui`. **Question:** How can a plain `Map` collapse duplicate in-flight HTTP requests — including ones racing inside one `Promise.all` — and what are the poison-cache consequences?

## Cache the promise, not the result
**Path/Symbol:** `packages/shadcn/src/registry/fetcher.ts:20-141` (`registryCache`, `fetchRegistry`, `getRegistryCacheKey`, `clearRegistryCache`).
**Signature:** `fetchRegistry(paths: string[], options?: { useCache?: boolean }) => Promise<any[]>`; internal `getRegistryCacheKey(url, headers) => `${url}:${sha256hex}``.
**Data Shape:** Module-level `Map<string, Promise<any>>`. Key = request URL + sha256 of the JSON-serialized header entries after lowercasing keys and sorting them (`localeCompare`) — so `{A:1,B:2}` and `{b:2,a:1}` hit one entry. Values are **promises**, stored before being awaited.

### Decisive source
```ts
const registryCache = new Map<string, Promise<any>>()

// inside paths.map(async path => ...):
const cacheKey = getRegistryCacheKey(url, headers)
if (options.useCache && registryCache.has(cacheKey)) {
  return registryCache.get(cacheKey)
}
const fetchPromise = (async () => {
  // ... build headers, fetchWithProxy, status→typed-error mapping ...
  return response.json()
})()
if (options.useCache) {
  registryCache.set(cacheKey, fetchPromise)   // BEFORE awaiting
}
return fetchPromise
```

**Flow:** resolve URL → read per-URL headers from ALS context → compute key → cache-hit returns the SAME shared promise (concurrent callers join the flight) → miss creates the IIFE promise, registers it synchronously, then both branches await it. `useCache:false` skips BOTH the read and the write (test proves two real network calls). `clearRegistryCache()` is the only eviction.
**Invariant:** The promise must be inserted into the map before any `await` of it; caching the *awaited result* instead would still race concurrent callers. Because rejected promises stay cached, a transient failure is remembered until `clearRegistryCache()` — porters must expose a clear/bypass path or add eviction.
**Probe:** `packages/shadcn/src/registry/fetcher.test.ts` — `:188-233` counts handler invocations across three sequential `fetchRegistry(["styles/new-york/button.json"])` calls with a 10ms-delayed handler: `fetchCount` stays `1`. `:93-124` proves two *concurrent* contexts with different `Authorization` headers get different cached responses (header hash separates keys). `:373-395` proves post-`clearRegistryCache()` re-fetch hits the server. Runner absent in checkout (node_modules missing) — pinned by direct test read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "shadcn-ui", query: "fetchRegistry cache key headers sha256", limit: 10 });
```

## Verdict
Adopt promise-before-await insertion, normalized-header key hashing, and the useCache-bypasses-read-and-write semantics as a portable micro-kernel for any dedupe-heavy client. Adapt hashing to your header model (the lowercase+sort normalization is what makes override tests pass). Omit the shadcn Accept/User-Agent defaults if your transport sets its own content negotiation.
