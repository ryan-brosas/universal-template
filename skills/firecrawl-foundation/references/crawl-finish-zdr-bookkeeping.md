<!-- capsule-v2 -->
# Crawl finish detection + ZDR bookkeeping — when is a crawl "done", and what state must be wiped at finish?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I detect crawl completion from scattered job sets and honor zero-data-retention on the bookkeeping itself?

## Crawl finish + ZDR bookkeeping
**Path/Symbol:** `apps/api/src/lib/crawl-redis.ts`:`isCrawlFinished` (:291-301) / `isCrawlKickoffFinished` (:303-314) / `finishCrawl` (:338-373) / `recordThreatBlocked` (:93-106) / `addCrawlJobDone` (:195-220).
**Signature:** `isCrawlFinished(id): Promise<boolean>` (private); `finishCrawl(id, logger?)`; `recordThreatBlocked(crawlId, url, decision): Promise<boolean>` — true only for FIRST record of that URL in this crawl.
**Data Shape:** Redis keys (all 24h EXPIRE, refreshed on read): `crawl:<id>` doc (JSON StoredCrawl incl. queueBackend pg|fdb, webhook/requestId ride-alongs), `:jobs` set, `:jobs_qualified` set, `:jobs_done` set, `:jobs_donez_ordered` zset (score = completion epoch ms; FAILED jobs are ZREM'd out), `:sitemap_jobs`/`:sitemap_jobs_done`, `:kickoff:finish` marker, `:visited`/`:visited_unique`, `:threat_blocked` hash (canonical URL → ThreatDecision JSON).

### Decisive source
```ts
async function isCrawlFinished(id) {
  return (await scard("crawl:"+id+":jobs_done")) === (await scard("crawl:"+id+":jobs"))
      && (await isCrawlKickoffFinished(id));   // kickoff marker present AND sitemap jobs all done
}
export async function recordThreatBlocked(crawlId, url, decision): Promise<boolean> {
  const isNew = await redisEvictConnection.hsetnx(key, url, JSON.stringify(decision));
  return isNew === 1;   // doubles as the crawl-scoped BILLING dedup for blocked discoveries
}
// finishCrawl: set :finish, srem active_crawls + crawls_by_team_id, then EAGER deletes:
await del("crawl:" + id + ":visited");
await del("crawl:" + id + ":visited_unique");
await del("crawl:" + id + ":threat_blocked");   // unconditional — keeps ZDR even if crawl doc unreadable
```

**Flow:** every member job completion calls `addCrawlJobDone` (success ⇒ ZADD ordered zset with now; failure ⇒ ZREM so status pages never see it); a finish job on the `crawlFinishedQueue` re-checks `isCrawlFinished`, runs `finishCrawlSuper` (webhook etc.), which calls `finishCrawl`. Blocked-discovery records use HSETNX so a site-wide nav link pointing at one blocked URL bills its scan fee ONCE per crawl regardless of how many pages rediscovered it.
**Invariant:** Completion = jobs_done == jobs AND kickoff finished AND sitemap done — forgetting any conjunct finishes crawls early (status pages then miss late results). The threat_blocked delete is UNCONDITIONAL (comment: "deleting it unconditionally keeps the ZDR guarantee even when the crawl document is missing or unreadable at finish time") — gating it on getCrawl() success would leak URLs precisely in the broken case.
**Probe:** anchored at repo root `apps/api/src`: `grep -c 'hsetnx' lib/crawl-redis.ts` → 1; `grep -n 'threat_blocked' lib/crawl-redis.ts` → exactly 2 hits (:98 key build, :372 finish-time delete; the doc comment says "threat-protection bookkeeping" not the literal).
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "finishCrawl isCrawlFinished threat_blocked hsetnx", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt set-cardinality completion checks + HSETNX-scoped billing dedup + unconditional ZDR wipes for distributed job orchestration; adapt key layout; omit the pg/fdb dual-backend field unless porting the queue migration.
