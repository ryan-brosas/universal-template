<!-- capsule-v2 -->
# Engine waterfall race — how do engines run concurrently yet degrade in a strict order?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I overlap engine attempts so slow engines don't block the ladder but quality still degrades predictably?

## Engine waterfall race
**Path/Symbol:** `apps/api/src/scraper/scrapeURL/index.ts`:`scrapeURLLoop` (:660-943) + `scrapeURLLoopIter` (:513-646) + `WrappedEngineError` (:648-658).
**Signature:** `scrapeURLLoop(meta): Promise<ScrapeUrlResponse>`; per-engine `scrapeURLLoopIter(meta, engine, snipeAbort)`.
**Data Shape:** `enginePromises: {engine, unsupportedFeatures, promise}[]` grows as engines are waterfalled in list order; each iteration races ALL live engine promises + a `waitUntilWaterfall` timer (only while `remainingEngines.length > 0`) + an outer abort/timeout timer (`meta.abort.scrapeTimeout() ?? 300000`).

### Decisive source
```ts
const waitUntilWaterfall = getEngineMaxReasonableTime(meta, engine) + config.SCRAPEURL_ENGINE_WATERFALL_DELAY_MS;
enginePromises.push({ engine, unsupportedFeatures, promise: (async () => {
  try { return { engine, unsupportedFeatures, result: await scrapeURLLoopIter(meta, engine, snipeAbort) }; }
  catch (error) { throw new WrappedEngineError(engine, error); }   // every failure carries its engine id
})() });
result = await Promise.race([ ...enginePromises.map(x => x.promise),
  ...(remainingEngines.length > 0 ? [waterfallTimer] : []),
  outerAbortTimer ]);
```

**Flow:** shift next engine → start its promise immediately → race; on `WrappedEngineError`: x-twitter failures are FATAL re-throws (:804-808); plain `EngineError`/`IndexMissError`/`EngineUnsuccessfulError`/`FEPageLoadFailed`/engine-tier `AbortManagerThrownError` are logged-and-swallowed then the failed engine is filtered out and the race continues with survivors; terminal classes (AddFeatureError, RemoveFeatureError, SiteError, SSLError, DNSResolutionError, ActionError, UnsupportedFileError, PDFAntibotError, PDFOCRRequiredError, DocumentAntibotError, PDFInsufficientTimeError, ProxySelectionError, NoCachedDataError, AgentIndexOnlyError, XTwitterConfigurationError, LLMRefusalError, non-engine aborts, ScrapeJobTimeoutError) rethrow out of the loop entirely. On `WaterfallNextEngineSignal` (timer fired): break inner loop and waterfall the NEXT engine — previous promises KEEP RUNNING and can still win the race.
**Invariant:** The success gate inside `scrapeURLLoopIter` is content-shaped, not exception-shaped: markdown non-empty (via ≤300KB check path `MAX_HTML_SIZE_FOR_MARKDOWN_CHECK`, onlyMainContent first with full-content fallback), 2xx/304 status, no `error` field ⇒ success; otherwise `throw new EngineUnsuccessfulError(engine)` which the loop deliberately logs NOTHING for ("~48k lines/hour across all engines" comment :825-834). A porter who turns EngineUnsuccessful into a hard failure breaks every soft-decline waterfall.
**Probe:** anchored at repo root `apps/api/src`: `grep -c 'SCRAPEURL_ENGINE_WATERFALL_DELAY_MS' scraper/scrapeURL/index.ts` → 1; `grep -c 'EngineUnsuccessfulError' scraper/scrapeURL/index.ts` → 3 (import + throw :641 + instanceof :825); `grep -n '300000' scraper/scrapeURL/index.ts` → 1 hit at :797 fallback max timeout.
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "scrapeURLLoop WaterfallNextEngineSignal WrappedEngineError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt race-with-waterfall-timer + error-carries-engine-id for multi-strategy fetch ladders; adapt the terminal-vs-swallowed error classification to your domain's retry semantics; omit fire-engine-specific FEPageLoadFailed quirks.
