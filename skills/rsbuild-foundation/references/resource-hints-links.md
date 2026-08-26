<!-- capsule-v2 -->
# Preload/prefetch link synthesis — why are hints injected into assetTags.styles and deduped against script srcs?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the chunk→file→link pipeline: html-scoping, filter algebra, crossorigin rules, and the styles-array injection point.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/rspack-plugins/resource-hints/HtmlResourceHintsPlugin.ts` — defaults 32–35, `applyFilter` 54–119, `mergeResourceHints` 135–157, `generateLinks` 159–252 (sort 207, as/crossorigin 218–241), apply hooks 283–307; driver `plugins/resourceHints.ts` (inline excludes 35–38, exclude merge 40–59, plugin registration 107–141); helpers doesChunkBelongToHtml.ts (`recursiveChunkGroup` visited-set 29–46, `recursiveChunkEntryNames` 48–57), extractChunks.ts, getResourceType.ts.
**Signature:** `new HtmlResourceHintsPlugin(options, type:'preload'|'prefetch', HTMLCount, isDev, getHTMLPlugin)`.
**Data Shape:** ResourceHintsOptions `{type:'async-chunks'|'all-assets'|'initial', include?, exclude?, dedupe}`; options may be an ARRAY → independent groups merged in order.

### Decisive source
```ts
const htmlChunks = options.type === 'all-assets' || HTMLCount === 1
  ? extractedChunks
  : extractedChunks.filter((chunk) => doesChunkBelongToHtml({...}));   // multi-HTML: scope per page
const allFiles = htmlChunks.reduce((acc, c) => acc.concat([...c.files, ...(c.auxiliaryFiles||[])]), [])
  .filter((f) => !(isDev && f.endsWith('.hot-update.js')) && !f.endsWith('.map'));   // always drop maps/hot
const sortedFilteredFiles = [...new Set(allFiles)].filter(applyFilter).sort();        // predictable output
if (attributes.as === 'font') attributes.crossorigin = '';              // fonts REQUIRE CORS mode
if ((as==='script'||as==='style') && crossOriginLoading && !(crossOriginLoading!=='use-credentials' && publicPath==='/'))
  attributes.crossorigin = crossOriginLoading === 'anonymous' ? '' : crossOriginLoading;
```
```ts
// alterAssetTags: links PREPEND to styles array — before scripts, after nothing:
data.assetTags.styles = [...mergeResourceHints(this.resourceHints, data.assetTags.scripts), ...data.assetTags.styles];
// dedupe key `${rel}:${href}`, first group wins; dedupe:true also drops links whose href IS a script src
```

**Flow:** include filters are OR-ed (any match keeps file); if ANY include exists and none matches the file is dropped; excludes OR to DROP. Inline-chunk'd assets auto-excluded by unioning their regex tests into exclude. preload adds `as` from extension table (script/style/image/font/track/fetch) while prefetch omits it deliberately (low priority).
**Invariant:** (1) `.map`/`.hot-update.js` exclusion is unconditional — hinting source maps is always wrong; (2) sort() before emission or HTML output diffs churn between builds; (3) font preload without crossorigin='' downloads twice (fetch mode ≠ CORS mode).
**Probe:** unit `packages/core/tests/resourceHints.test.ts:4/:13/:22` (getResourceType script/image/track table); e2e `cases/html/*` resource families.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "HtmlResourceHintsPlugin mergeResourceHints getResourceType doesChunkBelongToHtml", limit: 8 });
```

## Verdict
Adopt scoped extraction, include-OR/exclude-OR algebra, deterministic sort, rel:href dedupe with script-src collision removal, and the styles-array injection point. Adapt `as` inference table to your asset types. Omit vue-preload-webpack-plugin lineage details.
