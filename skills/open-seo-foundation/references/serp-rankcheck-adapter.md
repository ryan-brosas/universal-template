<!-- capsule-v2 -->
# SERP rank-check adapter — how do you extract "my ranking" from an advanced SERP payload and cut crawl cost at the same time?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** How is the target domain's position derived, and how does stop_crawl_on_match avoid recording false misses?

## Organic-only position extraction + early-stop crawl control
**Path/Symbol:** `src/server/lib/dataforseo/serp.ts:buildRankCheckResult` (:119-142), `stopCrawlOnTarget` (:34-44), `fetchRankCheckSerp` (:144-183), `clampSerpDepth` (:22-24), `postRankCheckTasks` (:202-279), `fetchRankCheckTaskResult` (:293-334).
**Signature:** `function buildRankCheckResult(input: { keywordId: string; keyword: string; targetDomain: string }, items: SerpLiveItem[]): RankCheckResult` where result = `{ keywordId, keyword, position: number | null, url: string | null, serpFeatures: string[] }`.
**Data Shape:** Items are passthrough-zod-validated SERP elements (`type`, `rank_group`, `rank_absolute`, `domain`, `url`, `etv`, …). Depth clamped to [10,100] (vendor bills in pages of 10).

### Decisive source
```ts
// Matching is restricted to organic results and uses with_subdomains, mirroring
// buildRankCheckResult exactly: without find_targets_in, a sitelink or PAA
// mention could stop the crawl before the domain's organic listing and record a
// false "not ranking".
const organicMatch = items.find((item) => {
  if (item.type !== "organic" || item.domain == null) return false;
  const domain = item.domain.toLowerCase();
  return domain === target || domain.endsWith(`.${target}`);
});
position: organicMatch ? (organicMatch.rank_group ?? organicMatch.rank_absolute ?? null) : null,
```

**Flow:** request google/organic live-advanced (or task_post/task_get for queued) with device-paired OS (`windows`/`android`) → 40501 no-results treated as empty set (valid for obscure keywords) → find FIRST organic item whose domain equals or is a subdomain of target → position = rank_group (organic-only rank users count) falling back to rank_absolute; serpFeatures = deduped item types → queued posts echo `tag: "${keywordId}:${device}"` so results map back WITHOUT relying on order; task_get collection is deliberately NOT metered (charged at post time — running it through the metering seam would double-bill).
**Invariant:** The early-stop rule and the extraction rule must mirror each other (`find_targets_in: ["organic"]`, `match_type: "with_subdomains"`): stopping on any feature type would truncate before the organic hit. rank_group ≠ rank_absolute (the latter counts local packs/PAA/AI overviews and reads worse than what users see).
**Probe:** `src/server/lib/dataforseo/endpoints.test.ts` + `grep -n "stop_crawl_on_match\|find_targets_in" src/server/lib/dataforseo/serp.ts` (organic-only restriction pinned).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "buildRankCheckResult stopCrawlOnTarget rank_group organic", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt organic-only matching + mirrored early-stop semantics + tag-based result correlation for ANY SERP vendor with advanced payloads. Adapt field names to your vendor's schema. Omit the local/maps variants if you don't track local packs.
