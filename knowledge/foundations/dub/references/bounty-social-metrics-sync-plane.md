<!-- capsule-v2 -->
# Bounty social-metrics sync plane — how do you keep third-party social metrics fresh for submissions without hammering the scraper?

**Source:** dub AGPL-3.0-or-later `main@29df217a2963`; Codebase Memory `dub`. **Question:** A social-content bounty stores a partner-submitted URL whose metrics (views/likes) change over time. What cache ladder, rate gate, and status-transition rule keep the external scraper bounded and the submission state machine honest?

## Connected graph-selected seam
**Path/Symbol:** `apps/web/app/(ee)/api/partner-profile/programs/[programId]/bounties/[bountyId]/social-content-stats/route.ts:GET` (:15-97) · `apps/web/lib/api/scrape-creators/get-social-content.ts:getSocialContent` (:39-248, esp. :44-95, :221) · `apps/web/app/(ee)/api/cron/bounties/sync-social-metrics/route.ts:POST` (:28-238) · `apps/web/lib/bounty/api/get-social-metrics-updates.ts:getSocialMetricsUpdates` (:25-95) · platform registry `apps/web/lib/bounty/social-content.ts` (:1-50).
**Signature:** route: `GET ?url=<httpUrl>` → SocialContent; cron: `POST {bountyId, startingAfter?}` under withCron; kernel: `getSocialMetricsUpdates({bounty, submissions}): Promise<SocialMetricsUpdate[]>`.
**Data Shape:** bounty.submissionRequirements is loose JSON — socialMetrics {platform, metric, minCount} extracted via safeParse (resolveBountyDetails, lib/bounty/utils.ts); submissions carry urls[] (first non-empty string only) + socialMetricCount + status.

### Decisive source
```ts
// getSocialContent cache ladder (:44-95, :221): 404s are NEGATIVE-CACHED 30 days, other errors are NOT cached
if (!url || !isValidUrl(url)) return EMPTY_SOCIAL_CONTENT;
url = normalizeUrl(url);
const cacheKey = `socialContentCache:${await hashStringSHA256(url)}`;
const cachedResult = await redis.get<SocialContent>(cacheKey);
if (cachedResult) return cachedResult;
const version = platform === "tiktok" ? "v2" : "v1";
const { data, error } = await scrapeCreatorsFetch("/:version/:platform/:contentType", {...});
if (error) {
  if (error.status === 404) waitUntil(redis.set(cacheKey, EMPTY_SOCIAL_CONTENT, { ex: CACHE_TTL * 24 * 30 }));  // 30-day negative cache
  return EMPTY_SOCIAL_CONTENT;   // transient errors NOT cached — retried next pass
}
...
waitUntil(redis.set(cacheKey, result, { ex: CACHE_TTL }));   // 1h positive TTL, written after response
```
```ts
// on-demand probe route gates (:26-36, :70-88): inline factory, NOT a named policy
const { success } = await ratelimit(10, "1 h").limit(`partner-profile:social-content-stats:${partner.id}`);
if (!success) throw new DubApiError({ code: "rate_limit_exceeded", ... });
...
if (!bountyInfo?.socialMetrics) throw new DubApiError({ code: "bad_request", message: "This bounty does not have social content requirements." });
const canSubmitBounty = canPartnerSubmitBounty({...});
if (!canSubmitBounty) throw new DubApiError({ code: "not_found", message: "Bounty not found." });   // submittability gate, oracle-suppressed
```
```ts
// sync cron walker (:25, :66-102, :111-124, :149-180, :211-235): batch 50, self-requeue, draft→submitted ONLY at minCount
const SUBMISSION_BATCH_SIZE = 50;
where: { bountyId, status: { notIn: [rejected, approved] } }, orderBy: { id: "asc" },
...(startingAfter && { skip: 1, cursor: { id: startingAfter } }), take: SUBMISSION_BATCH_SIZE,
const activeSubmissions = submissions.filter((s) => !isBountyEnded(getEffectiveBountyPeriod({ programEnrollment: s.programEnrollment, bounty }).endsAt));
const shouldTransitionToSubmitted = submission.status === "draft" && socialMetricCount >= minCount;
if (shouldTransitionToSubmitted) { updateData.status = "submitted"; updateData.completedAt = new Date(); notifications.push(...); }
await prisma.$transaction(updates);
if (submissions.length === SUBMISSION_BATCH_SIZE) { /* qstash.publishJSON self-requeue with last id */ }
else prisma.bounty.update({ where: { id: bountyId }, data: { socialMetricsLastSyncedAt: new Date() } });  // bounty stamp ONLY on final batch
```
**Flow:** partner probes a URL → per-partner 10/h rate gate → bounty must declare socialMetrics (safeParsed from JSON) → canPartnerSubmitBounty (not_found otherwise) → getSocialContent (validate → normalize → sha256-keyed Redis 1h → ScrapeCreators v1/v2 → 404 negative-cached 30d / transient not cached → per-platform field map). Cron walker: withCron POST → skip bounties without socialMetrics/minCount → page 50 open submissions (id cursor + skip:1) → drop expired per-partner windows → allSettled scrape fan-out with integer-only metric acceptance (Number.isInteger gate, get-social-metrics-updates.ts :82) → $transaction updates; draft→submitted flip with completedAt + batch email ONLY when count ≥ minCount → full page ⇒ self-requeue, final batch ⇒ stamp bounty.socialMetricsLastSyncedAt.
**Invariant:** (1) Negative results are cached LONGER than positive ones (30d vs 1h) so dead URLs never re-hit the scraper, while transient failures stay retryable — the asymmetry IS the availability contract. (2) The draft→submitted transition is owned by exactly one writer (the sync walker), gated on count ≥ minCount, and stamps completedAt in the same update; nothing else flips this edge. (3) The bounty-level lastSyncedAt stamp happens only when the walk EXHAUSTS (page < batch size), so a partially-processed bounty never looks fully synced. (4) The on-demand probe reuses the SUBMIT predicate (not the see predicate) and suppresses the existence oracle with not_found.
**Probe:** No direct test for the stats route or sync cron. Deterministic probes executed at pin: `ex: CACHE_TTL * 24 * 30` at get-social-content.ts:85 with CACHE_TTL=3600 at :10; `ratelimit(10, "1 h")` at social-content-stats/route.ts:26; `shouldTransitionToSubmitted` at sync cron :151 with `status === "draft" &&` guard; `submissions.length === SUBMISSION_BATCH_SIZE` self-requeue gate at :211; `Number.isInteger(socialMetricCount)` at get-social-metrics-updates.ts:82.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getSocialContent socialContentCache negative cache 404", limit: 5 }); // cache ladder
await mcp.codebase_memory.search_graph({ project: "dub", query: "sync-social-metrics SUBMISSION_BATCH_SIZE startingAfter draft submitted", limit: 5 }); // cron walker
```

## Verdict
Adopt the asymmetric cache ladder (long negative TTL for 404s, short positive TTL, no caching of transient errors, writes after response via waitUntil), the single-writer draft→submitted transition gated on a stored minCount, and the exhaust-before-stamp sync bookkeeping. Adapt the inline ratelimit(10,"1 h") to your policy table if you have one (this route deliberately bypasses named policies). Omit the per-platform field mapping unless you integrate the same scraper. Caveat: no direct test exists for this plane; anchors are line-pinned at the pin.
