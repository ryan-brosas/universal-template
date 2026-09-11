<!-- capsule-v2 -->
# Click-signal fraud pair — paid-traffic query-param fingerprint with Google allowlist, and banned-referral minimatch gate over BOTH referer fields

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** How does a click URL get attributed to an ad platform, and how can a program whitelist its own campaigns out of the paid-traffic flag?

## Two config-driven click rules with fail-closed config parsing
**Path/Symbol:** `apps/web/lib/api/fraud/rules/check-paid-traffic-detected.ts:checkPaidTrafficDetected` (:24-112) + `rules/check-referral-source-banned.ts:checkReferralSourceBanned` (:127-187).
**Signature:** both `evaluate: async ({ click }, rawConfig) => Promise<FraudTriggeredRule>`; configs parsed by per-rule zod schemas (`safeParse(rawConfig ?? defaultConfig)` — invalid stored config logs and returns `{triggered:false}`, never throws).
**Data Shape:** paid-traffic config `{platforms: PaidTrafficPlatform[] (default ["google"]), google:{whitelistedCampaignIds:string[]}}`; platform→param table `PAID_TRAFFIC_PLATFORMS_CONFIG` (constants.ts :345-385: google=[gclid,gad_source,gad_campaignid], facebook=[fbclid,fb_action_ids], x=[twclid], bing=[msclkid], linkedin=[li_fat_id], reddit=[rdclid], tiktok=[ttclid]); referral config `{domains: string[]}`.

### Decisive source
```ts
// paid traffic: scan configured platforms' params against the final click URL
for (const platform of config.platforms) { ... for (const qk of queryParamsKeys)
  if (foundPlatform.queryParams.includes(qk)) source = foundPlatform.id; }
if (source === "google") {
  const wl = config.google?.whitelistedCampaignIds?.filter(Boolean) ?? [];
  if (wl.length > 0) {
    const matched = ["gad_campaignid", "utm_campaign"].some((p) => {
      const v = queryParams[p]?.trim(); return v && wl.includes(v); });
    if (matched) return { triggered: false };   // whitelisted campaign ⇒ NOT fraud
  } }
if (source) return { triggered: true, metadata: { source, url: click.url } };

// referral ban: normalize domains + referrers, glob-match case-insensitively
const normalizedBannedDomains = config.domains.map(getDomainWithoutWWW).filter(Boolean);
const referrerCandidates = [click.referer, click.referer_url].filter(Boolean)
  .map(getDomainWithoutWWW).filter(Boolean);
if (minimatch(referrer, source, { nocase: true }))
  return { triggered: true, metadata: { source } };
```
(check-paid-traffic-detected.ts :54-106 / check-referral-source-banned.ts :146-181 condensed)

**Flow (paid):** empty-platforms or missing click.url ⇒ off → param scan (LAST matching platform in config order wins `source`) → google-only allowlist escape hatch via `gad_campaignid`/`utm_campaign` values. **Flow (referral):** zero normalized domains or neither referer field ⇒ off → double loop referrers×domains → first minimatch wins.
**Invariant:** (1) detection keys on AD CLICK IDS in the destination URL, never on headers/IP — cookie-deleted visitors still flag; (2) the allowlist checks TWO param names but only for google and only when non-empty after `filter(Boolean)`; (3) referral matching is domain-normalized on BOTH sides (`getDomainWithoutWWW`) and CASE-INSENSITIVE (`nocase:true`) with glob support (`*.spam.com` patterns legal); (4) metadata always records WHICH source fired (`source`) so dashboards can rank abuse channels.
**Probe:** anchored at dub repo root: `grep -o 'whitelistedCampaignIds' apps/web/lib/api/fraud/rules/check-paid-traffic-detected.ts | wc -l` = **6**; `grep -c 'platforms: \["google"\]' apps/web/lib/api/fraud/rules/check-paid-traffic-detected.ts` = **1** (default); `grep -o 'nocase' apps/web/lib/api/fraud/rules/check-referral-source-banned.ts | wc -l` = **1**; `grep -c 'click.referer, click.referer_url' apps/web/lib/api/fraud/rules/check-referral-source-banned.ts` = **1**. Direct tests: `tests/fraud/index.test.ts` paidTrafficDetected flow (:222-265) drives `?gclid=...&gad_source=1` expecting `metadata.source:"google"`; referralSourceBanned flow (:178-220) sets the referer header to the banned domain expecting `metadata.source` = that domain.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "checkPaidTrafficDetected", limit: 5 });
```

## Verdict
Adopt the param-table fingerprint + campaign allowlist pattern and the dual-referer glob gate. Adapt the platform table and match library. Omit the specific ad-platform param strings only if your market uses none of these networks.
