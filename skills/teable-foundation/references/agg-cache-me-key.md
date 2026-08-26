<!-- capsule-v2 -->
# lastModifiedTime-versioned agg cache — Me-sentinel key inflation + redlock stampede control

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How are aggregation endpoints cached for an hour yet never serve stale or cross-user results?

## Version = table.lastModifiedTime; key hash = djb2-ish 36-bit
**Path/Symbol:** `apps/nestjs-backend/src/features/aggregation/open-api/aggregation-open-api.controller.ts:getAggregationWithCache` (:54–101) applied to all seven GET handlers (:103–179); key builders `performance-cache/generate-keys.ts:generateAggCacheKey` (:12–19); hash `utils.ts:generateHash` (:1–8); Me check `utils/filter-has-me.ts` (:3–11); wrap engine `performance-cache/service.ts:wrap` (:309–375).
**Signature:** cacheKey = `` `agg:${path}:${tableId}:${lastModifiedTime?.getTime() ?? '0'}:${generateHash(query)}` ``; TTL 60*60.
**Data Shape:** Redis via Keyv namespace `teable_perf`; values wrapped `{data}`.

### Decisive source
```ts
const cacheQuery =
  filterHasMe(query?.filter) || filterHasMe(viewFilter)
    ? { ...query, currentUserId: this.cls.get('user.id') }
    : query;
const cacheKey = generateAggCacheKey('aggregation', tableId,
  table.lastModifiedTime?.getTime().toString() ?? '0', cacheQuery);
```
```ts
// utils.ts
let hash = 0;
for (let i = 0; i < str.length; i++) {
  hash = ((hash << 5) - hash + str.charCodeAt(i)) & 0xffffffff;
}
return Math.abs(hash).toString(36);
```

**Flow:** Every aggregation GET resolves the table's `lastModifiedTime` as VERSION (any write invalidates all cached stats for that table at once — no per-entry eviction), hashes the query, and wraps execution in `PerformanceCacheService.wrap`: get → miss → redlock(`perf:lock:`+key, 10s TTL auto-extend) → re-get inside lock → execute → set. On ResourceLocked/Execution error: sleep 50ms, retry read once, else execute unguarded. Cache disabled entirely when `BACKEND_PERFORMANCE_CACHE` unset (`isAvailable()` short-circuits to plain `fn()`).
**Invariant:** The Me-inflation rule is a correctness/privacy contract: any filter containing the `'Me'` sentinel (checked as substring in string OR JSON form — cheap but over-matches harmless tokens) makes the result user-specific, so currentUserId MUST enter the key or user A's "filter: created-by-Me" numbers would serve user B. Versioning by table mtime trades granularity for zero invalidation code — porters needing per-view precision need view mtimes too. The wrap's default `preventConcurrent:true` means one slow aggregate blocks siblings only via lock contention, and the fallback EXECUTES rather than errors — availability over dedup.
**Probe:** `grep -cF 'filterHasMe' apps/nestjs-backend/src/features/aggregation/open-api/aggregation-open-api.controller.ts` → 2; `grep -cF 'preventConcurrent: true' apps/nestjs-backend/src/performance-cache/service.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getAggregationWithCache generateAggCacheKey filterHasMe", limit: 10 });
```

## Verdict
Adopt mtime-versioned result caching with identity-sensitive key inflation; adapt the sentinel detection to your filter language; keep fail-open execution under lock errors.
