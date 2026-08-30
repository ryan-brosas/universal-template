<!-- capsule-v2 -->
# Credit estimation — how do you pre-estimate metered API credits so the estimate never understates the real charge?

**Source:** OpenSEO MIT `main@cd6a7820`; Codebase Memory `ext-open-seo`. **Question:** Where exactly do rounding and ceiling happen so an agent-facing cost estimate matches what billing will deduct?

## Per-call round-then-ceiling accumulation
**Path/Symbol:** `src/shared/rank-tracking.ts:estimateRankCheckCredits` (:75-103), `costPerSerpAtDepth` (:60-65).
**Signature:** `function estimateRankCheckCredits(keywordCount: number, devices: "both"|"desktop"|"mobile", depth: number, method: "live"|"queued"): { costUsd: number; costCredits: number }`.
**Data Shape:** Provider prices per SERP page of 10: live $0.0020 base + $0.0015 extra page; queued $0.0006 + $0.00045; `depth/10` pages; `devicesCount("both")=2`; queued meters `MAX_TASKS_PER_POST=100` pairs per call, live meters 1 pair per call.

### Decisive source
```ts
// Metering rounds and ceilings each provider call independently. Live rank
// checks make one call per keyword/device pair, while queued checks post up
// to MAX_TASKS_PER_POST pairs per call. Summing one aggregate and rounding
// once can therefore understate the credits that will actually be charged.
for (let offset = 0; offset < totalChecks; offset += checksPerMeteredCall) {
  const checksInCall = Math.min(checksPerMeteredCall, totalChecks - offset);
  const callCostUsd = roundUsdForBilling(
    checksInCall * costPerSerpAtDepth(depth, method) * SEO_DATA_COST_MARKUP,
  );
  costUsd += callCostUsd;
  costCredits += Math.ceil(callCostUsd * AUTUMN_SEO_DATA_CREDITS_PER_USD);
}
```

**Flow:** totalChecks = keywords × devices → iterate in provider-call-sized groups → per call: USD cost = checks × per-SERP price × markup, rounded to billing precision → credits = ceil(USD × credits-per-USD), accumulated per call → final aggregate USD rounded once more. The result feeds both the UI estimate and the workflow's maxCostCredits approval gate (`rankCheckCostApprovalError`: "…costs N credits, above the approved maximum of M. Call estimate_rank_tracker_cost again and ask the user to approve the updated amount.").
**Invariant:** Rounding must mirror the real metering granularity — rounding one aggregate instead of each call UNDERSTATES charges for live mode (one call per pair). Queued estimates are nominal task_post amounts; rejected/failed/timed-out tasks can later add live-fallback spend (documented, accepted). Scheduled checks estimate at QUEUED pricing even though they run through beginRankCheckRun — a live-price estimate would skip checks the user can afford.
**Probe:** `src/shared/rank-tracking.test.ts` (per-call vs aggregate rounding expectations) — verify with `grep -n "estimateRankCheckCredits" src/shared/*.test.ts src/server -r`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-open-seo", query: "estimateRankCheckCredits costUsd costCredits markup ceil", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the per-provider-call rounding loop and the ceil-per-call credit conversion as THE contract for any usage-based pricing surface. Adapt prices/markup/credits-per-USD constants to your vendor. Omit the DataForSEO live-vs-queued price table if your vendor bills uniformly.
