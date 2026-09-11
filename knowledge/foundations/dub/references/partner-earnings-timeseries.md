<!-- capsule-v2 -->
# Partner earnings timeseries — MySQL commission revenue zero-fill-joined onto warehouse analytics

**Source:** dub AGPL-3.0-or-later main@29df217a29631ced4041882a28d2327cc4546f27; Codebase Memory dub. **Question:** How do you enrich Tinybird click/lead/sale timeseries with money earnings that live in a DIFFERENT database (MySQL Commission table) without losing empty buckets?

## Enrollment-scoped analytics + three-way earnings join per groupBy
**Path/Symbol:** apps/web/app/(ee)/api/partners/analytics/route.ts:GET (:18-212); schemas partners.ts:partnerAnalyticsQuerySchema (:829-847), partnerAnalyticsResponseSchema (:857-871).
**Signature:** GET withWorkspace({workspace, searchParams}) -> count: {analytics, earnings} | timeseries: row[]+earnings | top_links: partnersTopLinksSchema-parsed rows. requiredPlan ["business","advanced","enterprise"] (:209-211).
**Data Shape:** query allows ONLY {partnerId|tenantId, interval/start/end/timezone/query, groupBy in [top_links,timeseries,count] default count}; earnings rows {start:string, earnings:number}.

### Decisive source
```ts
// tenant OR partner identity resolves ONE enrollment; message names which key missed
throwIfNoPartnerIdOrTenantId({ partnerId, tenantId });
const programEnrollment = await prisma.programEnrollment.findUnique({
  where: partnerId ? { partnerId_programId: {...} } : { tenantId_programId: {...} },
  include: { program: true, links: { orderBy: { clicks: "desc" } } },
});
// analytics restricted to THAT partner's links — ParsedFilter built from enrollment link ids
const analytics = await getAnalytics({ event: "composite", groupBy,
  linkId: parseFilterValue(programEnrollment.links.map((link) => link.id)), ... });   // :76

// timeseries branch: raw SQL buckets then ZERO-FILL merge onto warehouse rows
SELECT DATE_FORMAT(CONVERT_TZ(createdAt, '+00:00', ${timezone || '+00:00'}), ${dateFormat}) AS start,
       SUM(earnings) AS earnings FROM Commission WHERE earnings > 0 AND programId=... AND partnerId=...
       AND status IN ('pending','processed','paid') AND type='sale' AND createdAt >= start AND < end
       GROUP BY start ORDER BY start ASC;
const earningsLookup = Object.fromEntries(earnings.map((item) => [format(new Date(item.start),
  granularity === "hour" ? "yyyy-MM-dd'T'HH:00" : "yyyy-MM-dd'T'00:00"), { earnings: item.earnings }]));
return analytics.map((item) => ({ ...item,
  earnings: Number(earningsLookup[formattedDateTime]?.earnings ?? 0) }));
```
(route.ts :35-82 condensed, :124-168 condensed)

**Flow:** plan gate -> zod parse (groupBy enum narrows the FULL analyticsQuerySchema via pick+extend) -> enrollment lookup by partnerId XOR tenantId composite key (not_found names the missing kind :59-64; cross-workspace program ALSO demotes to not_found :66-71 — no existence oracle) -> getAnalytics scoped to enrollment link ids as a ParsedFilter -> three branches: count folds one Commission aggregate _sum into the analytics object (:92-118); timeseries runs the raw-SQL bucket query, keys both sides to yyyy-MM-ddTHH:00|00:00 strings, and zero-fills missing buckets with ?? 0 (:120-169); top_links matches Commission groupBy(linkId) sums onto enrollment links and whitelists through partnersTopLinksSchema.parse (:171-207).
**Invariant:** earnings eligibility is FROZEN at status in pending/processed/paid + amount>0 + type sale in ALL THREE branches — the same predicate expressed twice (Prisma where + raw SQL string) must stay in lockstep when edited. Bucket keys are timezone-shifted BEFORE formatting on BOTH sides; a mismatch silently zeroes buckets instead of erroring.
**Probe:** executed at pin: grep -n "parseFilterValue(programEnrollment.links" -> :76; grep -n CONVERT_TZ -> :128; grep -n "earnings ?? 0" -> :164,:203; sentinel concat n/a here. Coverage caveat: this file is parse_partial at :126 (tree-sitter flagged single line inside the template literal) — range :120-140 read DIRECTLY from source; graph output not trusted for that line. Direct test tests/partners/analytics.test.ts pins strict response parses for all three groupBy values (:8 allowedGroupBy, :26-32); describe.runIf(env.CI) gated (:10) — offline-blocked here.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", file_pattern: "partners/analytics", limit: 15 });
// observed: route Module 1-213 / GET Variable 18-212; tests.partners.analytics test Module 1-36
```

## Verdict
Adopt enrollment-scoped ParsedFilter scoping, the frozen eligibility triple, keyed-bucket zero-fill joining, and not_found demotion for cross-tenant probes. Adapt bucket formats and status vocabulary. Omit the EE wrapper (withWorkspace/default-program inference) if your tenancy model differs.
