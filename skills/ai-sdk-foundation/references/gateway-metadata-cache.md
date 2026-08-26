<!-- capsule-v2 -->
# Gateway metadata cache — why does a stale-while-revalidate cache swallow background refresh failures, and what does the first caller see?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does `getAvailableModels()` stay fast and correct under concurrent callers and a flaky gateway, without a request coalescing library?

## Hand-rolled SWR with promise dedupe
**Path/Symbol:** `packages/gateway/src/gateway-provider.ts:getAvailableModels` (429–453).
**Signature:** `const getAvailableModels = async (): Promise<GatewayFetchMetadataResponse>`.
**Data Shape:** Three closure slots: `pendingMetadata: Promise<...> | null` (in-flight or latest settled promise), `metadataCache: GatewayFetchMetadataResponse | null`, `lastFetchTime: number`. Refresh decision is `!pendingMetadata || now - lastFetchTime > cacheRefreshMillis` — note it tests the PROMISE SLOT, not cache presence, so a failed first-ever fetch leaves `pendingMetadata` as a rejected promise that is retried on the next call.

### Decisive source
```ts
if (!pendingMetadata || now - lastFetchTime > cacheRefreshMillis) {
  lastFetchTime = now;                       // staleness clock bumped BEFORE the fetch settles
  pendingMetadata = new GatewayFetchMetadata({ baseURL, headers: getHeaders, fetch })
    .getAvailableModels()
    .then(metadata => { metadataCache = metadata; return metadata; })
    .catch(async error => { throw await asGatewayError(error, await parseAuthMethod(await getHeaders())); });
}
return metadataCache ? Promise.resolve(metadataCache) : pendingMetadata;
```

**Flow:** call → fresh? start fetch (coalescing concurrent callers onto one promise) → return cached if any, else await the in-flight promise → after expiry, the NEXT call re-fetches while the old cache still serves.
**Invariant:** `lastFetchTime` is bumped at REQUEST START, so a slow/hung fetch does not spin retry loops — every caller during the hang gets the same pending promise. The `.catch` wrapper converts raw errors to Gateway errors but LEAVES `pendingMetadata` rejected; because the guard is `||`, a subsequent call after TTL starts a NEW fetch (self-healing), but within TTL with no cache every caller sees the same rejection. Porters who reset `pendingMetadata = null` in the catch change retry semantics.
**Probe:** `grep -c 'lastFetchTime = now' packages/gateway/src/gateway-provider.ts` → `1`; direct test `gateway-provider.test.ts` 'should cache metadata for the specified refresh interval' advances `_internal.currentDate` 9s→11s past a 10s TTL asserting `toHaveBeenCalledTimes(2)` (`grep -c 'expect(mockGetAvailableModels).toHaveBeenCalledTimes(2)' … → 2`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "getAvailableModels metadataCacheRefreshMillis pendingMetadata", limit: 10 });
```
Resolves line-exact: `getAvailableModels Function gateway-provider.ts 429-453`.

## Verdict
Adopt the three-slot SWR pattern verbatim for any remote catalog (model lists, tool registries); adapt the TTL default (5 min) and the `_internal.currentDate` test seam; omit nothing — the failure-path subtleties ARE the porting surface. Coverage caveat: none — behavior pinned by two direct caching tests plus error-conversion tests in gateway-fetch-metadata.test.ts.
