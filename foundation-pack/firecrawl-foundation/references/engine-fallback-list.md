<!-- capsule-v2 -->
# Engine fallback list builder — in what order do engines run, and which get filtered before the waterfall?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I build a quality-ordered, feature-aware engine candidate list with stealth/exchange/lockdown special cases?

## Engine fallback list builder
**Path/Symbol:** `apps/api/src/scraper/scrapeURL/engines/index.ts`:`buildFallbackList` (:589-914), `engineOptions` quality table (:232-557), `featureFlagOptions` priority table (:121-142).
**Signature:** `buildFallbackList(meta): Promise<{engine: Engine; unsupportedFeatures: Set<FeatureFlag>}[]>`.
**Data Shape:** `Engine` union of 15 ids (exchange / fire-engine;chrome-cdp[;stealth] / fire-engine(retry)… / tlsclient… / playwright / fetch / pdf / document / index / index;documents / wikipedia / x-twitter); each engine carries a full 16-flag `features` boolean map + integer `quality` (positive = general web, negative = specialty). Feature flags carry `priority` weights: pdf/document/audio/video=100, atsv/useFastMode=90, screenshot/location/mobile/skipTls/disableAdblock=10, actions/stealthProxy/branding=20, waitFor=1.

### Decisive source
```ts
const prioritySum = [...meta.featureFlags].reduce((a,x) => a + featureFlagOptions[x].priority, 0);
const priorityThreshold = Math.floor(prioritySum / 2);
...
if (supportScore >= priorityThreshold) {   // engine keeps only if it supports >= half the requested feature weight
  selectedEngines.push({ engine, supportScore, unsupportedFeatures });
}
// stealth explicitly requested => keep ONLY stealth-capable survivors (else negative-quality filter drops them)
if (meta.featureFlags.has("stealthProxy")) { ... }
// any positive-quality non-index survivor => drop ALL negative-quality (specialty) engines
if (selectedEngines.some(x => engineOptions[x.engine].quality > 0 && !x.engine.startsWith("index"))) {
  selectedEngines = selectedEngines.filter(x => engineOptions[x.engine].quality > 0);
}
// sort: supportScore desc, then effectiveQuality desc
selectedEngines.sort((a,b) => b.supportScore - a.supportScore || getEffectiveQuality(b.engine) - getEffectiveQuality(a.engine));
```

**Flow:** rawBase64 fast path → single chrome-cdp engine (or [] under lockdown/mock-less self-host) → Exchange single-engine bypass when `canUseExchangeForRequest` → flagged-org blocklist re-check that FAILS CLOSED to `[]` on error → lockdown/agentIndexOnly collapse the pool to `[index, index;documents]` → `shouldUseIndex` false splices index engines → when fire-engine is live and no fastMode/atsv/audio/video flag: drop `fetch` ALWAYS and `tlsclient` pair UNLESS engpicker said TlsClientOk → wikipedia kept only on Wikimedia URLs AND a coin flip (`Math.random() >= 0.5`) → x-twitter exclusive lock for X URLs → priority-threshold filter → stealth restriction → quality-sign partition → sort.
**Invariant:** The engpicker boost must be applied at SORT time (+50 ⇒ `fire-engine;tlsclient` becomes 60, above CDP's 50 but below index's 1000; +14 ⇒ stealth variant −15→−1), NOT by re-adding spliced engines — "the sort-time quality boost below cannot resurrect an engine that was spliced out here" (:757-763). Also: specialty engines (negative quality) can only survive when NO positive-quality general engine survived — this is what makes `pdf`/`document` reachable.
**Probe:** anchored at repo root `apps/api/src`: `grep -n 'priorityThreshold' scraper/scrapeURL/engines/index.ts` → exactly 2 hits (declaration :801 + use :835); `grep -c 'quality += 50' scraper/scrapeURL/engines/index.ts` → 1; `grep -c 'quality += 14' scraper/scrapeURL/engines/index.ts` → 1; `grep -n '>= 0.5' scraper/scrapeURL/engines/index.ts` → 1 hit inside the wikipedia coin-flip line.
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "buildFallbackList engine quality priority threshold", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-table design (per-engine feature matrix + per-feature weight) and threshold filtering for capability-based engine selection; adapt quality numbers and engine set; omit Exchange/blocklist org plumbing unless porting the whole access-control plane.
