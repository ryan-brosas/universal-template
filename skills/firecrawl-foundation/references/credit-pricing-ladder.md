<!-- capsule-v2 -->
# Credit pricing ladder — how does a scrape's feature set translate into credits, including failure billing?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I price a composite job (base + format surcharges + per-unit extras) and still bill failures honestly?

## Credit pricing ladder
**Path/Symbol:** `apps/api/src/lib/scrape-billing.ts`:`calculateCreditsToBeBilled` (:63-225) + `calculateThreatScanCredits` (:41-61); constants :17-31.
**Signature:** `calculateCreditsToBeBilled(options, internalOptions, document: Document | null, costTracking | toJSON, flags, error?, _unsupportedFeatures?, exchange?, threatDecisions?): Promise<number>` (number of credits).
**Data Shape:** additive ladder over a base of 1 credit/document; surcharge constants: lockdown +4; json format (or changeTracking json mode) SETS 5 (replace); deterministicJson sets 10 when this run generated the extractor script else 3 — detected via cost-ledger tag `metadata.module === "deterministic-json" && metadata.role === "codegen"`; fire-1 agent REPLACES with ceil(totalCost × 1800); question/query +4; highlights +4; audio +4; video +4; x-twitter postprocessor +29; ZDR +team flag `zdrCost ?? 1`; PDF pages beyond the first +1 each; redactPII +4 base AND +4 per extra PDF page; unblocked-domain bonus +4 when URL blocked for default rules but not for THIS team (`isUrlBlocked(u,null) && !isUrlBlocked(u,flags)`).

### Decisive source
```ts
if (document === null) {
  let creditsToBeBilled = 0;                                   // failures bill NO base cost...
  if (v1Agent?.model?.toLowerCase() === "fire-1" || v1JSONAgent...) {
    creditsToBeBilled = Math.ceil((costTrackingJSON.totalCost ?? 1) * 1800); // ...except fire-1 actuals
  }
  if (error instanceof TransportableError && error.code === "SCRAPE_LOCKDOWN_CACHE_MISS") creditsToBeBilled = 1;
  return creditsToBeBilled + threatScanCredits;                // ...but scans that already ran always bill
}
```

**Flow:** success ⇒ exchange-handled responses short-circuit to `getExchangeSuccessCredits`; else walk the additive ladder in order (each later rule may REPLACE rather than add: json=5, deterministicJson=10|3, fire-1=cost×1800) then append per-unit extras (PDF pages, redactPII pages) then threat-scan fees. Failure ⇒ 0 base + the two exceptions above + scan fees. Threat scan fee = +2 per UNIQUE consulted canonical URL within one billing scope; zscaler-mode decisions never bill (customer's own tenant); pre-URL-level decisions without `.url` bill individually so they don't collapse onto one undefined key.
**Invariant:** Ordering is load-bearing — replace-style rules must be evaluated after the base but their relative precedence (fire-1 wins over json/deterministicJson because it appears later) must not be reordered. The unblockedDomainCostBonus compares TWO blocklist evaluations (null flags vs team flags) — porting only one call silently bills nobody or everybody.
**Probe:** anchored at repo root `apps/api/src`: `grep -n 'threatScanCost = 2' lib/scrape-billing.ts` → exactly 1 hit at :31; `grep -c 'creditsToBeBilled +=' lib/scrape-billing.ts` → 8; `grep -n "role === \"codegen\"" lib/scrape-billing.ts` → 1 hit at :153.
**Probe:** direct test `apps/api/src/lib/scrape-billing.test.ts` pins: "bills X/Twitter scrapes at 30 credits" (:41), "bills deterministic JSON at 10 credits when the script was generated" (:121), "bills every distinct URL, including URLs sharing a domain" (:298), "bills once when the redirect re-check resolves to the same URL" (:402). Runner BLOCKED this window (no node_modules in clone) — anchors verified by grep only.
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "calculateCreditsToBeBilled threat scan credits", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt replace-vs-additive pricing ladder + failure-still-bills-consumed-services posture for usage metering; adapt surcharge table; omit Exchange/threat-protection specifics if you lack those subsystems.
