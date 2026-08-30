<!-- capsule-v2 -->
# Meta-object lifecycle — how is per-scrape mutable state threaded through an immutable-feeling pipeline?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I carry scrape id/options/flags/prefetches/cost through engine waterfall and transformers without a god-object rewrite?

## Meta-object lifecycle
**Path/Symbol:** `apps/api/src/scraper/scrapeURL/index.ts`:`buildMetaObject` (:318-448) + `Meta` type (:137-183) + `scrapeURL` (:1067-1116).
**Signature:** `buildMetaObject(id, url, options, internalOptions, costTracking): Promise<Meta>`; `scrapeURL(id, url, options, internalOptions, costTracking): Promise<ScrapeUrlResponse>`.
**Data Shape:** `Meta` = { id, url, rewrittenUrl?, options (defaults applied via `applyScrapeOptionsDefaults`), internalOptions, logger (child w/ scrapeId/teamId/crawlId/ZDR), abort: AbortManager, featureFlags: Set<FeatureFlag>, mock, pdfPrefetch/documentPrefetch/fetchPrefetch each tri-state `undefined | null | {...}`, costTracking, winnerEngine?, audioCookies?, threatDecisions: ThreatDecision[] }. Tri-state prefetch comment at :156: **undefined = no prefetch yet, null = prefetch came back empty**.

### Decisive source
```ts
// The meta object contains all required information to perform a scrape.
// The meta object is usually immutable, except for the logs array, and in edge cases (e.g. a new feature is suddenly required)
// Having a meta object that is treated as immutable helps the code stay clean and easily tracable,
const effectiveOptions = applyScrapeOptionsDefaults(options);
return {
  id, url, rewrittenUrl: rewriteUrl(url),
  options: effectiveOptions, internalOptions, logger,
  abortHandle,
  abort: new AbortManager(
    internalOptions.externalAbort,
    options.timeout !== undefined ? { signal: abortController.signal, tier: "scrape", ... } : undefined,
  ),
  featureFlags: buildFeatureFlags(url, effectiveOptions, internalOptions),
  ...
  pdfPrefetch, documentPrefetch, fetchPrefetch,
  costTracking, threatDecisions: [],
};
```

**Flow:** `buildMetaObject` applies URL-specific overrides (`urlSpecificParams[hostname.replace(/^www\./,"")]` merged via `Object.assign` BEFORE defaults :325-333), forces engine from path heuristics if unset, arms a `setTimeout(abort(new ScrapeJobTimeoutError()), options.timeout)` (:355-361), converts uploads into synthetic prefetch objects so downstream engines see one uniform shape (:367-412), then `scrapeURL` runs threat-protection pre-check → robots check → retry-tracked `scrapeURLLoop` → post-success redirect re-check. Mutability contract: only `featureFlags` (retry ladder), `pdfPrefetch`/`documentPrefetch` (AddFeatureError payload), `winnerEngine`, `audioCookies`, `threatDecisions` are ever reassigned after construction.
**Invariant:** A porter must keep the three-state prefetch distinction — collapsing `null` into `undefined` breaks both the PDFAntibotError guard (`if (meta.pdfPrefetch !== undefined) throw` :1280-1284, i.e. "already prefetched and still blocked ⇒ fail") and the actions-support skip (`pdfPrefetch === undefined` :682-683 means "browser never ran").
**Probe:** anchored at repo root `apps/api/src`: `grep -c 'prefetch came back empty' scraper/scrapeURL/index.ts` → exactly 3 (pdfPrefetch + documentPrefetch + fetchPrefetch comment blocks at :156/:166/:176).
**Probe:** anchored at repo root: `grep -n 'applyScrapeOptionsDefaults(options)' apps/api/src/scraper/scrapeURL/index.ts` → exactly 1 hit at line 414.
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "buildMetaObject Meta pdfPrefetch documentPrefetch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the meta-object pattern (one constructed context, enumerated mutation sites, tri-state prefetches) for any multi-engine fetch pipeline; adapt field set to your domain; omit Firecrawl-specific urlSpecificParams/teamId plumbing.
