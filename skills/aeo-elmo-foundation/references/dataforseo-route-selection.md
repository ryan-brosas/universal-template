<!-- capsule-v2 -->
# DataForSEO route selection — when does one provider id scrape and when does it call the model?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** How does a single provider serve three different upstream products (SERP, LLM Scraper, LLM Responses) and keep its advertised access honest?

## Route table + access mirror
**Path/Symbol:** `packages/lib/src/providers/registry/dataforseo.ts:SERP_MODELS` (L26), `LLM_MODELS` (L37–44), `SCRAPER_CALLS` (L55–76), `dataforseoAccess` (L91–94), `run()` dispatch (L349–366).
**Signature:** `dataforseoAccess({ model, version }): "scraped" | "api"`; `run(model, prompt, options)`.
**Data Shape:** three route sets — Google surfaces (`google-ai-mode`, `google-ai-overview`) always scraped; chatgpt/gemini scraped via the LLM Scraper UNLESS the target pins a version slug (then LLM Responses); perplexity has no scraper so it is always LLM Responses.

### Decisive source
```ts
function dataforseoAccess({ model, version }: ModelConfig): ProviderAccess {
	if (SERP_MODELS.has(model) || model === AI_OVERVIEW_MODEL) return "scraped";
	return !version && model in SCRAPER_CALLS ? "scraped" : "api";
}
// run() mirrors it exactly:
if (!options?.version && model in SCRAPER_CALLS) return runLlmScraper(...);
if (LLM_MODELS[model])          return runLlmResponse(model, prompt, options);
```

**Flow:** settings page renders the label from `accessFor`; `run()` dispatches by the same predicate; `validateTarget` rejects a version slug on any scraped surface ("that surface is scraped, not requested by model — [a pin there] would silently do nothing") and requires `:online` on every DataForSEO target because all served surfaces always search.
**Invariant:** the label function and the dispatch MUST agree — a target labelled "Scraped" that actually asks the model directly describes the wrong data to the customer. The comment says exactly this; coverage.test.ts pins both sides.
**Probe:** `packages/lib/src/providers/registry/dataforseo.test.ts` route-selection describe: unpinned ChatGPT hits `chatGptLlmScraperLiveAdvanced` with `force_web_search: true`, pinned routes to `chatGptLlmResponsesLive`; `validateTarget` rejects pin-on-scraped (`dataforseo.test.ts:171`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "dataforseoAccess SERP_MODELS SCRAPER_CALLS runLlmScraper runLlmResponse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the route-table-plus-mirror-predicate shape for any multi-product vendor adapter; adapt the specific model ids/defaults (gpt-5.5, sonar, gemini-2.5-flash are pinned concrete models because vendor `-chat-latest` aliases lag the consumer product); omit the force_web_search flag if your scraper honors per-request search toggles.
