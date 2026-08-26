<!-- capsule-v2 -->
# Citation extraction dispatch — how do nine raw payload shapes become one citation stream?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** Where should per-provider citation parsing live so historical rows stay readable after the extractor improves?

## Read-time shape auto-detect
**Path/Symbol:** `packages/lib/src/text-extraction.ts:extractCitations` (L807–837), `extractTextContent` (L376–406), `isDataforseoScraperResult` (L64–66), `parseCitationUrl` (L429–441).
**Signature:** `extractCitations(rawOutput: any, providerOrEngine: string): Citation[]`; `Citation = { url, title?, domain, citationIndex }`.
**Data Shape:** `domain = new URL(url).hostname.replace(/^www\./,"")`; invalid URLs are skipped (never thrown); `citationIndex` is the dense first-seen order across the whole run; every extractor de-dupes on exact URL with a `seen` Set.

### Decisive source
```ts
// The dataforseo provider routes to three different DataForSEO products, so
// stored rows under that one provider id carry three shapes.
function isDataforseoScraperResult(result: any): boolean {
	return typeof result?.markdown === "string" || Array.isArray(result?.sources);
}
// … items.some(item => Array.isArray(item?.sections)) → LLM Responses delegate;
// otherwise items[].type === "ai_overview" .references[].
```
The dispatch keys on provider id with legacy aliases (`"openai"|"chatgpt"` → OpenAI extractor; `"google-ai-mode"|"google-ai-overview"` → dataforseo) because persisted runs may predate provider columnning.

**Flow:** run time stores normalized citations AND the untouched `rawOutput`; display/report paths re-read stored rows through these extractors. ChatGPT's scraper `search_results` array is deliberately ignored — those are results the model was SHOWN, not sources it cited; only top-level `sources` + per-item copies count.
**Invariant:** shown-results ≠ cited-sources is the core AEO measurement honesty rule; mixing them inflates citation counts with pages the answer never referenced.
**Probe:** `packages/lib/src/text-extraction.test.ts:258` ("de-dupes repeated URLs and ignores non-http entries"), `:272` (dispatch auto-detect reaches the LLM extractor through both `extractCitationsFromGoogle` and `extractCitations(raw,"dataforseo")`); dataforseo.test.ts:182 pins search_results exclusion.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "extractCitations parseCitationUrl isDataforseoScraperResult seen dedupe", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt read-time extraction over stored raw payloads — it makes schema drift in vendor APIs a re-deploy instead of a backfill; adapt the field ladders to your vendors (each extractor is an ordered probe list like `["markdown","text"]`); omit nothing — even the fallback `tryGenericExtraction` ladder is reusable for unknown providers.
