<!-- capsule-v2 -->
# GitDiffCache TTL + single-flight — how are repeated git-diff reads collapsed without stampede or stale-after-failure?

**Source:** Continue (Apache-2.0) `main@5522c6f44ca0ac3528b37244818fbfa39b5af470`; Codebase Memory `continue`. **Question:** How does a cached async fetch avoid both concurrent duplicate requests and caching a failure?

## Singleton cache with pendingRequest dedup
**Path/Symbol:** `core/autocomplete/snippets/gitDiffCache.ts` (whole, 73L).
**Signature:** `GitDiffCache.getInstance(getDiffFn: GetDiffFn, cacheTimeSeconds?: number): GitDiffCache`; `get(): Promise<string[]>`; `invalidate(): void`.
**Data Shape:** `cachedDiff: string[] | undefined` (undefined = never fetched), `lastFetchTime`, `pendingRequest: Promise | null`; default TTL 60s.

### Decisive source
```ts
public async get(): Promise<string[]> {
  if (this.cachedDiff !== undefined && Date.now() - this.lastFetchTime < this.cacheTimeMs)
    return this.cachedDiff;                      // fresh hit
  if (this.pendingRequest) return this.pendingRequest;   // single-flight: join in-flight fetch
  this.pendingRequest = this.getDiffPromise();
  return this.pendingRequest;
}
private async getDiffPromise(): Promise<string[]> {
  try {
    const diff = await this.getDiffFn();
    this.cachedDiff = diff;                       // success path ONLY updates the cache
    this.lastFetchTime = Date.now();
    return this.cachedDiff;
  } catch (e) {
    console.error("Error fetching git diff:", e);
    return [];                                    // fail-OPEN to empty, cache untouched
  } finally { this.pendingRequest = null; }       // release the flight slot even on error
}
```

**Flow:** `get()` checks freshness → joins an in-flight request if one exists → else starts a fetch that, on success, stamps value + time; on ANY throw resolves `[]` while leaving the previous good cache intact.
**Invariant:** Failures resolve to EMPTY ARRAY and do NOT poison the cache (`cachedDiff` only assigned after success) — a transient git failure degrades diff-snippets for one call instead of serving stale data forever or rejecting the completion pipeline. The `pendingRequest` slot clears in `finally` so a failed fetch doesn't wedge future callers onto a dead promise. Note for porters: `getInstance(getDiffFn, ...)` keeps the FIRST factory — later args are ignored (test-pinned singleton identity).
**Probe:** `core/autocomplete/snippets/gitDiffCache.vitest.ts` — six tests: cached-within-TTL calls getDiffFn once (:9), refresh after expiration (:22), "returns empty array on error" (:34), "reuses pending request" (:42), invalidate clears (:65), singleton instance (:77).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "continue", query: "GitDiffCache getDiffsFromCache single flight", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt TTL-cache + join-in-flight + fail-open-to-empty with success-only stamping as the pattern for any expensive IDE-side read feeding latency-sensitive prompts; adapt TTL and value type; omit nothing — all four behaviors are load-bearing and test-pinned.
