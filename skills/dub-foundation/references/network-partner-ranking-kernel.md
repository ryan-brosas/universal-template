<!-- capsule-v2 -->
# Network partner ranking kernel — how do you rank 1.5M network partners for discovery without trusting per-program performance alone?

**Source:** dub AGPL-3.0-or-later `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** how does the discover tab rank partners across the whole network, and which parts of the score are portable vs product-specific?

## Network partner ranking kernel
**Path/Symbol:** `apps/web/lib/api/network/calculate-partner-ranking.ts:calculatePartnerRanking` (:69-381) with `buildOrderByClause` (:46-64) and `buildDiscoverablePartnersFilter` (:125-145); sole caller `apps/web/app/(ee)/api/network/partners/route.ts:GET` discover arm (:120-131).
**Signature:** `calculatePartnerRanking({ programId, partnerIds?, country?, starred?, sortBy = "relevance", platform?, page = 1, pageSize, similarPrograms = [] }): Promise<Array<any>>`.
**Data Shape:** `similarPrograms: Array<{ programId, similarityScore }>` pre-filtered by the route to similarityScore > PROGRAM_SIMILARITY_SCORE_THRESHOLD (0.3), take 10, desc. Returns raw SQL rows (p.* + score columns) post-processed in-kernel to repair MySQL JSON typing.

### Decisive source
```ts
// :125-131 — the alias-parameterized discoverable filter reused by SIX subqueries
const buildDiscoverablePartnersFilter = (alias: string) => {
  const conditions: Prisma.Sql[] = [
    Prisma.sql`${Prisma.raw(alias)}.networkStatus IN ("approved", "trusted")`,
  ];
  if (partnerIds && partnerIds.length > 0) {
    conditions.push(
      Prisma.sql`${Prisma.raw(alias)}.id IN (${Prisma.join(partnerIds)})`,
    );
  }
  if (country) {
    conditions.push(
      Prisma.sql`${Prisma.raw(alias)}.country = ${country}`,
    );
  }
  return Prisma.join(conditions, " AND ");
};
```

**Flow:** base conditions (:78-82: networkStatus IN approved/trusted, COALESCE(clickToConversionRate,0) < 1, ignoredAt IS NULL OR no DiscoveredPartner row, enrolled.id IS NULL) → optional partnerIds/country/platform-EXISTS/starred filters (:84-119) → inner subquery `FROM (SELECT p_sub.* FROM Partner p_sub WHERE <discoverable filter>) p` cuts ~1.5M candidates to ~5k BEFORE joins (comment :131) → seven LEFT JOINs (current-program enrollment ×2, DiscoveredPartner, all-program metrics, similar-program metrics, categories, earning structures, sales channels, platforms), each aggregate subquery re-applying the SAME filter via the alias helper → finalScore = hasProfile(500) + trusted(200) + COALESCE(similarityScore,0) + COALESCE(programMatchScore,0) (:244-250) → ORDER BY (starred ⇒ dp.starredAt DESC :50; sortBy=subscribers+platform ⇒ correlated MAX(subscribers) subquery DESC :53-60; else finalScore DESC, p.id ASC :63) → LIMIT/OFFSET → JSON hydration repair (platforms string-or-parsed, try/catch → [], BigInt re-typing of subscribers/posts/views, Date re-typing of verifiedAt, :352-381).
**Invariant:** the discoverable-partner filter is enforced at the driver AND inside every aggregate subquery — dropping any one re-opens the 1.5M-row scan; the two dominance bonuses (profile 500, trusted 200) always outrank the 0-65 performance band, so a profile-less high performer can never outrank a profiled partner; `p.id ASC` is the deterministic tiebreak that keeps pagination stable.
**Probe:** no direct test (grep tests/ = ∅); deterministic probes: buildDiscoverablePartnersFilter ×8 occurrences (driver + six subqueries + helper def), `THEN 500 ELSE 0` :246, `THEN 200 ELSE 0` :248, `LEAST(50,` :174, `LEAST(15,` :204, `p.id ASC` :60/:63, `1.5M to 5,000` comment :131, FORCE INDEX ×3, JSON_ARRAYAGG :321, BigInt(platform.subscribers) :363; negative: exactly one caller of calculatePartnerRanking (the route discover arm).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "calculatePartnerRanking partner ranking discover", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the subquery-first funnel with an alias-parameterized eligibility helper re-applied at every join, the additive score with two hard dominance bonuses, and the deterministic id tiebreak. Adapt the score weights/ladder constants (500/200/50/15, 0.3 threshold, log-scaled 10%/15%/5% ladders) and the FORCE INDEX hints to your schema. Omit the ACME_PROGRAM_ID exclusion and the specific Prisma model names as product-specific. Coverage caveat: no direct test exists; evidence is whole-file source reads + executed grep probes at the pin.
