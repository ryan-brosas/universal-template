<!-- capsule-v2 -->
# Link-stats aggregation kernel — what does every metrics-based workflow assume about how partner stats are computed?

**Source:** dub AGPL-3.0-or-later `main@e3a558d1cf5d`; Codebase Memory project `dub`. **Question:** Where must the null/zero/bigint semantics of per-partner metric aggregation live so every consumer (orchestrator, campaigns, bounty) agrees?

## aggregatePartnerLinksStats: reduce with zero-defaults and cents normalization
**Path/Symbol:** `apps/web/lib/partners/aggregate-partner-links-stats.ts:aggregatePartnerLinksStats` (:9-40).
**Signature:** `aggregatePartnerLinksStats(links?: PartnerLink[] | null): { totalClicks, totalLeads, totalConversions, totalSales, totalSaleAmount }`.
**Data Shape:** input = array of link stat columns (`clicks/leads/conversions/sales` numbers; `saleAmount: number | bigint`); output all numbers.

### Decisive source
```ts
if (!links || links.length === 0) {
  return { totalClicks: 0, totalLeads: 0, totalConversions: 0,
           totalSales: 0, totalSaleAmount: 0 };        // ZEROES, never null
}
return links.reduce((acc, link) => {
  acc.totalSaleAmount += toCentsNumber(link.saleAmount);  // bigint → number at ONE site
  ...
}, { totalClicks: 0, ... });
```
(:10-17 empty contract; :26 cents fold)

**Flow:** consumers (`execute-workflows.ts:184-185`, send-campaign `buildWorkflowContext`, move-group context build) feed it enrollment links and read only the totals they expose to condition evaluation.
**Invariant:** (1) empty/null input yields an ALL-ZERO object — evaluators then compare `0 >= threshold`, which is exactly the desired "new partner hasn't qualified" behavior; returning null would force every caller into null-guards and silently disable conditions; (2) `saleAmount` arrives as bigint from Prisma sum columns and is normalized through `toCentsNumber` in exactly one place — callers never see mixed numeric types; (3) `totalCommissions` is deliberately NOT here (it needs its own aggregate query — see workflow-trigger-dispatch's lazy gate).
**Probe:** deterministic probe: `grep -c 'toCentsNumber' apps/web/lib/partners/aggregate-partner-links-stats.ts` = 2; behavior pinned indirectly by `tests/workflows/move-group-workflow.test.ts` threshold moves (metrics flow through this kernel).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", query: "aggregatePartnerLinksStats", limit: 5 });
// → dub.apps.web.lib.partners.aggregate-partner-links-stats.aggregatePartnerLinksStats @ aggregate-partner-links-stats.ts 9-40
```

## Verdict
Adopt zero-object-over-null aggregation with single-site bigint normalization for any metrics-conditioned engine. Adapt field set. Omit nothing — keep it tiny.
