<!-- capsule-v2 -->
# TTL cache key namespacing — how are responses cached across requests, and which results must never be cached?

**Source:** aeo-affiliate-skills MIT `main@ed17ef37bc167b52d9596cbe0292507f001c483d`; Codebase Memory `aeo-affiliate-skills`. **Question:** When one in-memory cache serves several endpoints of a daemon, how do you namespace keys and where does cacheability differ per endpoint?

## Lazy-TTL Map with evict-oldest, three call-site key namespaces
**Path/Symbol:** `tools/src/cache.ts`:`ProgramCache` (16–59), `server.ts`:`cacheKey` (37–39) with call sites :97 (`/search`), :126 (`/top`), :157 (`/info`).
**Signature:** `get(key: string): Program[] | null`; `set(key: string, data: Program[]): void`; `stats(): { entries: number; maxEntries: number; oldestAge: string }`; `function cacheKey(params: SearchParams): string` → `JSON.stringify(params)`.
**Data Shape:** `Map<string, {data: Program[], timestamp: number, key: string}>`, `CACHE_TTL_MS = 5*60*1000`, `maxEntries = 200`, exported as module singleton `export const cache`.

### Decisive source
```ts
get(key: string): Program[] | null {
  const entry = this.entries.get(key);
  if (!entry) return null;
  if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
    this.entries.delete(key);
    return null;
  }
  return entry.data;
}

set(key: string, data: Program[]): void {
  // Evict oldest if at capacity
  if (this.entries.size >= this.maxEntries) {
    const oldest = Array.from(this.entries.entries()).sort(
      (a, b) => a[1].timestamp - b[1].timestamp
    )[0];
    if (oldest) this.entries.delete(oldest[0]);
  }
  this.entries.set(key, { data, timestamp: Date.now(), key });
}
```

And the endpoint asymmetry that is the real trap:

```ts
// /search — caches whatever came back, including empty arrays:
programs = response.data;
cache.set(key, programs);

// /info — only non-empty results become cacheable:
if (programs.length > 0) cache.set(key, programs);
```

**Flow:** `/search` keys by `JSON.stringify(params)`; `/top` needs the same params shape as `/search` but a different result set, so it keys `{...params, _cmd: "top"} as any`; `/info` uses the string template `` `info:${name}` ``. On read: miss → fetch upstream → set. TTL expiry is lazy (checked only on `get`, expired entries deleted then); capacity eviction scans all entries for the oldest timestamp when full.
**Invariant:** An empty array is truthy — so `/search` serves an empty result from cache for the whole TTL window (no refetch storm against a temporarily empty upstream view), while `/info` deliberately leaves misses uncached so a retry after upstream ingestion can succeed. Preserve this asymmetry per endpoint semantics; don't "fix" it globally.
**Probe:** Deterministic source pins: `grep -n "CACHE_TTL_MS\|maxEntries" tools/src/cache.ts` → :8, :18; `grep -n 'info:' tools/src/server.ts` → :157 (string-namespace key); `grep -n '_cmd' tools/src/server.ts` → :126. Executed GREEN — see verification.md P6/P7.
**Coverage caveat:** none — both files checked `no_recorded_issue` at generation 2026-08-25T08:24:56Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aeo-affiliate-skills", query: "cacheKey ProgramCache ttl eviction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy expiry-on-read plus oldest-timestamp eviction as the minimal correct shared cache for a single-process daemon; adopt explicit key namespaces per endpoint when one store serves different result semantics. Adapt the O(n) eviction scan to an LRU structure only if your maxEntries grows orders of magnitude beyond 200. Omit caching empty `/search` pages if your upstream distinguishes "no matches" from "index temporarily empty" — here conflation is accepted to absorb upstream flakiness.
