<!-- capsule-v2 -->
# BrightData/Oxylabs/Cloro shape ladders — how do scraper vendors' shifting payloads get parsed?

**Source:** Elmo (aeo-elmo) MIT `main@da87272c`; Codebase Memory `ext-aeo-elmo`. **Question:** What extraction strategy survives vendor payload drift across AI Overview and chatbot datasets?

## Ordered probe ladders + defensive tree walks
**Path/Symbol:** `packages/lib/src/text-extraction.ts:collectAioSnippets` (L235–252), `extractBrightdataAiOverviewText` (L256–272), `extractTextFromBrightdata` (L274–295), `oxylabsAiOverviews` (L301–304), `extractOxylabsAiOverviewText` (L306–319), `extractTextFromOxylabs` (L321–342), `cloroAnswer` (L350–354), `extractTextFromCloro` (L356–369); citation twins at L660–800.
**Signature:** `extractTextFromBrightdata(rawOutput): string`; `extractCitationsFromOxylabs(rawOutput): Citation[]`.
**Data Shape:** BrightData: `ai_overview` first (markdown→text→aio_text→content→answer, then snippet-tree walk over `["list","texts","items","blocks","paragraphs"]` keys depth-capped 8), then answer-field ladder. Oxylabs: overview blocks probe BOTH nested-results and top-level shapes ("the wrapping has shifted across Oxylabs revisions"); citations from `["citations","external_links","links","sources"]` + Perplexity's nested `additional_results.sources_results`, with Google-AI-Mode `{urls:[...]}` group expansion. Cloro: `"aioverview" in rawOutput ? rawOutput.aioverview : rawOutput`.

### Decisive source
```ts
// BrightData suffixes AI Overview reference titles with UI noise like
// ". Opens in new tab." Cut it at a plain indexOf and trim the trailing
// punctuation — no backtracking regex over the (uncontrolled) title.
const marker = title.toLowerCase().indexOf("opens in new tab");
if (marker === -1) return title.trim();
return title.slice(0, marker).replace(/[.\s]+$/, "").trim();
```
Cloro note: `sources` = reference panel, `citationPills` = inline denormalized subset; Google's Shopping deep links inside them STAY (the citations page splits them out by URL); `relatedLinks` is deliberately NOT read — offered links ≠ cited sources.

**Flow:** each extractor is a pure function over stored rawOutput; every rung trims and skips empties; all de-dupe URLs via the shared seen-set pattern.
**Invariant:** uncontrolled vendor strings never hit backtracking regexes; "shown alongside" fields are never conflated with "cited" fields.
**Probe:** `packages/lib/src/providers/registry/{brightdata,oxylabs,cloro}.test.ts` + text-extraction.test.ts (all GREEN in probe run).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-elmo", query: "extractTextFromBrightdata extractCitationsFromOxylabs cloroAnswer stripAioTitleNoise", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ladder-style extractors for any third-party parsed payload; adapt field names per vendor revision; omit the tree walk only if your vendor guarantees flat snippets.
