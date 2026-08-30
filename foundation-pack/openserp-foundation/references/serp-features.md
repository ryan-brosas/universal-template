<!-- capsule-v2 -->
# SERP features — how are AI summaries/PAA/related-searches extracted declaratively without garbage?

**Source:** OpenSERP MIT `main@29c7b0fb`; Codebase Memory `ext-aeo-openserp`. **Question:** What gates keep selector-swept SERP modules content-bearing, deduped, and free of CSS shells and placeholder text?

## Spec-driven extraction
**Path/Symbol:** `core/feature_selectors.go:SerpFeatureSelector/ExtractSerpFeaturesBySelectors` (L88–141), `blockAwareText` (L27–85), `AttachFeaturesToFirstResult/StripResultFeatures/DeduplicateSerpFeatures` (L143–181), `google/features.go` (specs + placeholder filters), `core/page_helpers.go:FeaturesFromPageWithWait` (L297–305).
**Signature:** `ExtractSerpFeaturesBySelectors(doc, []SerpFeatureSelector) []SerpFeature`; `FeaturesFromPageWithWait(ctx, page, extract func(*goquery.Document) []SerpFeature)`.
**Data Shape:** SerpFeature{id f_md5_8, engine, type, title, text, items[], links[], source_result_ids[], position{absolute}, confidence, extracted_at}.

### Decisive source
```go
// emit ONLY content-bearing containers:
if feature.Text == "" && len(feature.Items) == 0 && len(feature.Links) == 0 { return true /*skip*/ }
matched = true
return !spec.SingleMatch     // one logical module even if containers nest
// block-aware flattening keeps structure without per-word div noise:
var blockLevelTags = {p, br, li, tr, pre, h1..h6, blockquote}
// div/section deliberately EXCLUDED: Google's streaming AI Overview wraps
// every word in its own <div>.
// placeholder/CSS-shell rejection (google/features.go):
"ai overview is not available", "обзор от ии недоступен", "show more"/"show less",
looksLikeCSS: "@keyframes"|"@media" OR ("{ " AND ": ">20 AND ";">20)
```

**Flow:** browser path scrolls to bottom then waits 2 s hydration before snapshotting; features ride out of parsers glued to results[0].Features (`AttachFeaturesToFirstResult`, creating a synthetic carrier result when the SERP had zero organic rows); raw path strips them unless query.Features; the response builder splits them onto top-level serp_features via AppendEnrichedSearchResult, back-linking source_result_ids; answer-box/snippet/knowledge/local typed rows WITHOUT parser features are MIRRORED into features (shouldMirrorResultAsFeature). Feature-relative links resolve against a per-engine base URL map.
**Invariant:** a container that yields nothing emits nothing; overlapping selectors dedupe via key type|title|text|firstItem|firstLink; blockAwareText collapses intra-node whitespace but preserves single edge spaces so inline fragments keep word gaps.
**Probe:** `go test ./core ./google ./bing -run SerpFeatures` (serp_features_test.go suites per engine); `TestGoogleParseHTMLEmptyHTML`.
**Probe executed (real runner):** the multi-package form ran only core's 6 (Go applies -run per listed package; google/bing suites have no "SerpFeatures" in names) — repaired: per-engine feature suites live under TestParseHTML*/TestFeatureItemsUseTextAsTitleAndStripInvisibleCharacters/TestAppendEnrichedSearchResult* and are green inside each package's whole-run (core+google+bing all ok); TestGoogleParseHTMLEmptyHTML = PASS inside `./google`.
**Python-equivalent probe (executed):**
```bash
grep -n 'SingleMatch' core/feature_selectors.go google/features.go | head -5   # spec flag wired at emit gate
grep -c 'placeholder\|looksLikeCSS' google/features.go                          # → 4 guard sites
```

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-openserp", query: "SerpFeatureSelector AttachFeaturesToFirstResult blockAwareText shouldMirrorResultAsFeature", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the spec struct, content-bearing gate, SingleMatch, and mirror rule; adapt container selectors continuously (they rot fastest of anything here); omit confidence values unless you feed a downstream ranker.
