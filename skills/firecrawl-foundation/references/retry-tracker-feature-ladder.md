<!-- capsule-v2 -->
# Retry tracker + feature-flag mutation ladder — how does the pipeline retry by mutating capabilities instead of re-running?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I bound an adaptive retry loop where each attempt changes feature flags rather than repeating work?

## Retry tracker + feature-flag ladder
**Path/Symbol:** `apps/api/src/scraper/scrapeURL/retryTracker.ts`:`ScrapeRetryTracker` (:18-89) + outer loop in `apps/api/src/scraper/scrapeURL/index.ts` (:1221-1316).
**Signature:** `new ScrapeRetryTracker({maxAttempts, maxFeatureToggles, maxFeatureRemovals, maxPdfPrefetches, maxDocumentPrefetches}, logger)`; `tracker.record(reason, lastError)` throws `ScrapeRetryLimitError(reason, stats)` when a per-reason OR global cap is crossed.
**Data Shape:** `ScrapeRetryStats = {totalAttempts, addFeatureAttempts, removeFeatureAttempts, pdfAntibotAttempts, documentAntibotAttempts}`; limits come from `config.SCRAPE_MAX_ATTEMPTS / SCRAPE_MAX_FEATURE_TOGGLES / SCRAPE_MAX_FEATURE_REMOVALS / SCRAPE_MAX_PDF_PREFETCHES / SCRAPE_MAX_DOCUMENT_PREFETCHES`.

### Decisive source
```ts
// retryTracker.ts: global gate checked FIRST, then per-reason
record(reason, lastError) {
  this.stats.totalAttempts += 1;
  if (this.stats.totalAttempts > this.config.maxAttempts) this.throwLimit("global", lastError);
  switch (reason) {
    case "feature_toggle": ... if (addFeatureAttempts > maxFeatureToggles) throwLimit ...
    case "pdf_antibot":   ... if (pdfAntibotAttempts > maxPdfPrefetches) throwLimit ...
}
// index.ts outer while(true): errors are CONTROL SIGNALS
catch (error) {
  if (error instanceof AddFeatureError && (forceEngine === undefined || Array.isArray(forceEngine))) {
    retryTracker.record("feature_toggle", error);
    meta.featureFlags = new Set([...meta.featureFlags].concat(error.featureFlags));
    if (error.pdfPrefetch) meta.pdfPrefetch = error.pdfPrefetch;       // engine hands back its prefetch
  } else if (error instanceof RemoveFeatureError && ...) {
    meta.featureFlags = new Set([...meta.featureFlags].filter(x => !error.featureFlags.includes(x)));
  } else if (error instanceof PDFAntibotError && forceEngine === undefined) {
    if (meta.pdfPrefetch !== undefined) { throw error; }               // prefetched AND still blocked = fatal
    meta.featureFlags.delete("pdf");                                   // drop pdf flag => chrome-cdp prefetch path next round
  } else { throw error; }
}
```

**Flow:** any engine throws Add/Remove/PDFAntibot/DocumentAntibot → tracker counts → flags mutated on the SAME meta → `while(true)` re-enters `scrapeURLLoop` with rebuilt fallback lists → until success or a cap throws `ScrapeRetryLimitError` carrying the full stats snapshot.
**Invariant:** Feature-mutation retries are refused when engines are pinned (`forceEngine` set and not an array) — a forced-engine scrape must fail honestly instead of silently switching capability sets. The global `maxAttempts` counter increments for EVERY reason class, so per-class caps can never exceed the global budget. The tracker records BEFORE mutating — order matters because record() may throw, aborting the mutation.
**Probe:** anchored at repo root `apps/api/src`: `grep -c 'retryTracker.record' scraper/scrapeURL/index.ts` → 4 (feature_toggle, feature_removal, pdf_antibot, document_antibot); `grep -n 'totalAttempts > this.config.maxAttempts' scraper/scrapeURL/retryTracker.ts` → exactly 1 hit at :38.
**Probe:** direct test (runner blocked this window — deterministic anchor): `grep -n 'SCRAPE_RETRY_LIMIT' scraper/scrapeURL/error.ts` → 1 hit at :700 (error code string).
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "ScrapeRetryTracker record retry limit", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt error-as-control-signal retry with a two-level budget ledger (global + per-reason) for adaptive pipelines; adapt reason classes to your domain; omit PDF/document-specific prefetch hand-back unless porting file scraping.
