<!-- capsule-v2 -->
# Transformer stack ordering — in what order do post-engine document fields derive, and why can't it be reordered?

**Source:** firecrawl AGPL-3.0 @ main`ca0be9b7d91eb9b48d3430f5678211f0d47e1d90`; Codebase Memory `ext-firecrawl`. **Question:** How do I build a format-conditional document-enrichment pipeline where each stage depends on the previous stage's fields?

## Transformer stack
**Path/Symbol:** `apps/api/src/scraper/scrapeURL/transformers/index.ts`:`transformerStack` (:643-667) + `executeTransformers` (:669-694) + `coerceFieldsToFormats` (:366-640).
**Signature:** `type Transformer = (meta, document) => Document | Promise<Document>`; stack executed SEQUENTIALLY (comment: "TODO: allow some of these to run in parallel"); rawBase64 requests skip everything but `coerceFieldsToFormats`.
**Data Shape:** Document fields accumulate: rawHtml → html → markdown → links/images/branding/metadata → json/summary/answer/highlights → diff/audio/video; final stage DELETES every field not present in requested formats.

### Decisive source
```ts
const transformerStack: Transformer[] = [
  deriveHTMLFromRawHTML,        // requires rawHtml
  deriveMarkdownFromHTML,       // requires html; SKIPS when onlyMainContent yields empty => full-content retry
  performCleanContent, performRedactPII,      // redactPII spans are MARKDOWN char offsets — needs markdown first
  deriveLinksFromHTML,          // doubles as indexer link-discovery forwarder (INDEXER_TRAFFIC_SHARE random gate)
  deriveImagesFromHTML, deriveBrandingFromActions,
  deriveMetadataFromRawHTML,    // engine metadata wins: {...extracted, ...document.metadata}
  fetchProduct, fetchMenu,
  ...(useIndex ? [sendDocumentToIndex] : []), ...(useSearchIndex ? [sendDocumentToSearchIndex] : []),
  performLLMExtractUnlessNativeJson, performDeterministicJson, performSummary, performQuery,
  performAttributes, performAgent, removeBase64Images, deriveDiff, fetchAudio, fetchVideo,
  coerceFieldsToFormats,        // LAST: strip unrequested fields
];
// every dependency stage guards:
if (document.rawHtml === undefined) throw new Error("rawHtml is undefined -- this transformer is being called out of order");
```

**Flow:** winner engine result → sequential transform with per-stage child loggers + timing ledger (`executions` array logged at debug) → coerceFieldsToFormats deletes unrequested fields (with "this is wasteful and indicates a bug" warnings for expensive fields like screenshot) and v1-compat keeps `document.extract` or `.json` per `internalOptions.v1OriginalFormat`.
**Invariant:** markdown derivation must run BEFORE redactPII (spans index into markdown) and BEFORE llmExtract (extraction consumes markdown); metadata derivation spreads ENGINE metadata OVER extracted so engines keep authority (:49-52); content-type shortcuts bypass HTML conversion (`application/json` wraps in a code fence, `text/plain` passes through UNTOUCHED because conversion escapes underscores). The empty-mainContent fallback rebuilds html from rawHtml with `onlyMainContent:false` — it must re-derive HTML, not reuse the filtered one.
**Probe:** anchored at repo root `apps/api/src`: `grep -n 'transformerStack' scraper/scrapeURL/transformers/index.ts` → exactly 2 hits (:643 decl, :679 use); `grep -c 'out of order' scraper/scrapeURL/transformers/index.ts` → 6 (four throw sites + two guard messages).
## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-firecrawl", query: "executeTransformers transformerStack coerceFieldsToFormats", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ordered dependent-stage enrichment with out-of-order guards and terminal field stripping for document pipelines; adapt stages/formats; omit Firecrawl's indexer traffic-share forwarding unless running an index product.
