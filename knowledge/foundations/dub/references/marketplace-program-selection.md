<!-- capsule-v2 -->
# Marketplace program selection — how do you build a storefront home page (featured/popular/new/category rows) from one query without N+1 or duplicate rows?

**Source:** dub AGPL-3.0-or-later `main@29df217a29631ced4041882a28d2327cc4546f27`; Codebase Memory `dub`. **Question:** how does the partner-facing program marketplace assemble its home-page sections, and where does ordering actually happen — SQL or JS?

## Marketplace program selection
**Path/Symbol:** `apps/web/lib/fetchers/get-marketplace-programs-summary.ts:getMarketplaceProgramsSummary` (:179-231, with selectPrograms :95-115, selectCategoryRows :119-177); `apps/web/app/(ee)/api/network/programs/route.ts:GET` (:14-139); `apps/web/app/(ee)/api/network/programs/count/route.ts:GET` (:14-133).
**Signature:** `getMarketplaceProgramsSummary(): Promise<MarketplaceProgramsSummary>` (react `cache()`-wrapped); route: `GET` with getNetworkProgramsQuerySchema params.
**Data Shape:** one findMany over programs with addedToMarketplaceAt NOT NULL including the DEFAULT_PARTNER_GROUP (slug-pinned) with its four reward relations + discount, plus categories. Returns {featuredPrograms, mostPopular, newPrograms, categories: Record<Category, Program[]>} behind MarketplaceProgramsSummarySchema.parse.

### Decisive source
```ts
// programs/route.ts :112-127 — post-fetch JS ordering, not SQL
    .sort((a, b) =>
      // if requesting featured programs, randomize the order
      featured
        ? Math.random() - 0.5
        : // if sorting by popularity, sort by marketplaceRanking first, then total invoice paid out
          sortBy === "popularity"
          ? a.marketplaceRanking - b.marketplaceRanking ||
            b.invoices.reduce((acc, invoice) => acc + invoice.amount, 0) -
              a.invoices.reduce((acc, invoice) => acc + invoice.amount, 0)
          : 0,
    )
```

**Flow:** summary kernel: fetch ALL marketplace programs once (cache()-memoized per request) → toProgramMeta computes each program's primary category (alphabetically-first label) → featured = featuredOnMarketplaceAt filter + Math.random() shuffle → mostPopular = selectPrograms by marketplaceRanking asc → newPrograms = by addedToMarketplaceAt desc → selectCategoryRows fills per-home-category rows to MARKETPLACE_HOME_ROW_PAGE_SIZE with a two-pass fill: primary-category pass, then a missed-primary backfill that reassigns programs whose primary category row is full into underfilled rows — ALL under one shared usedIds Set so no program appears in two sections. List route: SQL-side where (search contains over name/slug/domain/url/description, category some, rewardType via the default group's reward-id columns, status via enrollment none/some with status null = not-enrolled) + SQL orderBy, then the post-fetch JS sort above (featured shuffle; popularity tiebreak by total invoice amount — the reason invoices are included). Count route: raw-SQL twin with ONE commonWhereSql whose facet filters are groupBy-conditional (a facet never filters on itself: rewardType dropped when groupBy=rewardType, category when groupBy=category, status when groupBy=status) and three GROUP BY arms (category / rewardType / status) + a plain count, all bigint→Number converted at the boundary.
**Invariant:** every selection pass consumes and updates the SAME usedIds set — cross-section dedup is the kernel's core property; facet filters in the count route must be dropped for their own groupBy dimension or every facet count collapses to zero; rewardType/status/category filters always resolve through the DEFAULT_PARTNER_GROUP or ProgramEnrollment, never a denormalized program column.
**Probe:** no direct test (grep tests/ = ∅); deterministic probes: cache(async :179, usedIds ×10 refs, selectCategoryRows :119 + missedPrimary :136-172, Math.random() - 0.5 :205 (summary) and programs/route.ts :115, marketplaceRanking asc :101/:118, addedToMarketplaceAt :28, DEFAULT_PARTNER_GROUP.slug ×4 across list+count, groupBy !== "rewardType" :30 (count), Number(_count) ×2, invoices tiebreak :118-119; negative: no SQL-side RANDOM()/RAND() ordering — randomization is JS post-fetch in both files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "getMarketplaceProgramsSummary selectCategoryRows usedIds marketplace home", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the one-query + in-memory selection-passes kernel with a shared used-id ledger and the two-pass category backfill; adopt the groupBy-conditional facet where for count badges. Adapt the section list, row page size, category taxonomy, and the marketplaceRanking column. Omit the Math.random() featured shuffle if you need deterministic caching (note it breaks any HTTP-cache key on the summary route). Coverage caveat: no direct test exists; evidence is whole-file source reads + executed grep probes at the pin.
