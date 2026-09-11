<!-- capsule-v2 -->
# URL permutation dedup — how does one crawl lock treat http/https, www, and index-page variants as the same URL?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I dedupe crawler frontier URLs across scheme/host/index-file spelling variants with a single set key?

## URL permutation dedup
**Path/Symbol:** `apps/api/src/lib/crawl-redis.ts`:`generateURLPermutations` (:412-486) + `lockURL` (:488-537) + `normalizeURL` (:383-397).
**Signature:** `generateURLPermutations(url: string | URL): URL[]` (up to 16 variants); `lockURL(id, sc, url): Promise<boolean>` — true iff this URL was NEW for the crawl.
**Data Shape:** permutations = {with-www × without-www} × {http × https} × {slash / bare / index.html / index.php path forms}, deduped via `new Set(hrefs)`; hash-based routes (`#/`, `#!/`, len>2) keep their hash in normalizeURL, all others stripped; query string dropped when `crawlerOptions.ignoreQueryParameters`.

### Decisive source
```ts
// Contract comment (:399-411) — the invariants are the API:
// 1. non-zero permutations for all valid URLs
// 2. generateURLPermutations(url) == generateURLPermutations(generateURLPermutations(url)[n])
//    (idempotence: any member re-permutes to the SAME set, content AND order)
// 3. disjoint permutation sets for significantly different URLs
// Points 1+2 proven in permu-refactor.test.ts; point 3 accepted unproven.
if (!sc.crawlerOptions?.deduplicateSimilarURLs) {
  pipeline.sadd("crawl:" + id + ":visited", normalizedUrl);
} else {
  pipeline.sadd("crawl:" + id + ":visited", generateURLPermutations(normalizedUrl)[0].href);
}
const results = await pipeline.exec();
const res = (results?.[0]?.[1] as number) !== 0;   // SADD returns 0 when member already existed
```

**Flow:** discovery → `normalizeURL` (query-strip + hash policy) → optional permutation collapse into ONE canonical key → `SADD` into `crawl:<id>:visited` (pipeline with EXPIRE 24h) → SADD arity decides admission; admitted URLs also join `:visited_unique` whose cardinality enforces `crawlerOptions.limit` BEFORE the sadd. Failure of the limit pre-check returns false WITHOUT adding. `finishCrawl` deletes both visited sets eagerly (:363-365) instead of waiting out the TTL.
**Invariant:** Only `permutation[0]` is stored — correctness relies on invariant #2 (idempotence), NOT on storing all variants. A porter who "fixes" this to store all permutations changes limit accounting (visited_unique stays normalized but visited balloons). The limit check reads `scard(:visited_unique) >= limit` BEFORE sadd — race window exists by design and is resolved by SADD's 0/1 return.
**Probe:** anchored at repo root `apps/api/src`: `grep -c 'generateURLPermutations' lib/crawl-redis.ts` → 5 (contract comment ×2 :401/:403, def :412, lockURL call site :517, lockURLs call site :567).
**Probe:** direct test `apps/api/src/lib/permu-refactor.test.ts` :303-308 ("Proof that generateURLPermutations is stable": any member re-permutes identically). Runner BLOCKED this window.
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "generateURLPermutations lockURL visited", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt canonical-permutation dedup + SADD-arity admission for crawl frontiers; adapt variant axes (e.g. add trailing-slash-only if your corpus needs it); omit Redis eviction-layer specifics.
