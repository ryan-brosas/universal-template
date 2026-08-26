<!-- capsule-v2 -->
# CostTracking ledger — how do LLM call costs accumulate into a billable total with a hard limit?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I build a per-job usage ledger that both bills and enforces a spend ceiling mid-run?

## Cost tracking ledger
**Path/Symbol:** `apps/api/src/lib/cost-tracking.ts`:`CostTracking` (:12-57) + `CostLimitExceededError` (:1-7); consumed by `lib/scrape-billing.ts` (`calculateCreditsToBeBilled`) and threaded through `Meta.costTracking`.
**Signature:** `new CostTracking(limit: number | null = null)`; `.addCall({type: "smartScrape"|"other", metadata, cost, model, tokens?})`; `.toJSON(): {calls, smartScrapeCallCount, smartScrapeCost, otherCallCount, otherCost, totalCost}`.
**Data Shape:** each call appends `{...call, stack}` where stack is captured AT RECORD TIME via `new Error().stack!.split("\n").slice(2).join("\n")` — the caller's stack minus Error-internal frames.

### Decisive source
```ts
const nanProof = (n: number | null | undefined) => (isNaN(n ?? 0) ? 0 : n ?? 0);

public addCall(call) {
  this.calls.push({ ...call, stack: new Error().stack!.split("\n").slice(2).join("\n") });
  if (this.limit !== null && this.toJSON().totalCost > this.limit) {
    throw new CostLimitExceededError();      // throws AFTER the offending call is recorded
  }
}
public toJSON() { // NaN-poisoned costs never contaminate totals
  totalCost: this.calls.reduce((acc, c) => acc + nanProof(c.cost), 0),
}
```

**Flow:** every LLM invocation site (smartScrape / extract / summary / deterministicJson codegen…) calls `costTracking.addCall(...)`; billing later reads either the live instance or its serialized `toJSON()` snapshot (`calculateCreditsToBeBilled` accepts BOTH — `costTracking instanceof CostTracking ? .toJSON() : costTracking`, scrape-billing :85-86), so jobs can persist the ledger and bill in a different process.
**Invariant:** The limit check happens inside addCall AFTER push — the overspending call itself appears in the ledger (auditability over atomicity). Totals are computed through `nanProof` so a single NaN cost cannot poison `totalCost`. Billing code must treat the serialized shape as the cross-process contract, not the class.
**Probe:** anchored at repo root `apps/api/src`: `grep -n 'slice(2).join' lib/cost-tracking.ts` → exactly 1 hit at :33; `grep -c 'nanProof' lib/cost-tracking.ts` → 4 occurrences (1 def :9 + 3 reduction uses).
**Probe:** direct test exists at `apps/api/src/__tests__/snips/v2/billing.test.ts` and `src/lib/scrape-billing.test.ts` (vitest; runner blocked this window — no node_modules in clone).
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "CostTracking addCall limit totalCost", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt append-only ledger + record-time stack capture + NaN-proof reduction + throw-after-record limit for LLM spend accounting; adapt cost units; omit the smartScrape type split if you have no such sub-product.
