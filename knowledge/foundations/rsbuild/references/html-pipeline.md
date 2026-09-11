<!-- capsule-v2 -->
# HTML pipeline — how do tags flow through html plugin hooks, inlining, crossorigin/nonce post-passes?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know the tag lifecycle order (alterAssetTagGroups → modifyHTMLTags → tagConfig apply → modifyHTML beforeEmit), the title/favicon one-time injections, and how inline-chunk deletion preserves source maps.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/rspack-plugins/RsbuildHtmlPlugin.ts:apply` (241–453) — favicon emit (242–345), alterAssetTagGroups tap (363–425), beforeEmit→modifyHTML (427–451), `applyTagConfig` (128–211), `getTagPriority` (85–95); plugin side `plugins/html.ts:getTemplate` (43–84), `pluginHtml.setup` (198–333); inline pass `plugins/inlineChunk.ts` (245–318); security post-passes `plugins/html.ts:modifyHTMLTags order:'post'` (335–358) and `plugins/nonce.ts` (40–63).
**Signature:** `class RsbuildHtmlPlugin { constructor(getExtraData, getHTMLPlugin); apply(compiler) }`; entry linkage via `entryNameSymbol` on plugin options.
**Data Shape:** HtmlExtraData `{entryName, context, environment, favicon?, faviconDistPath, tagConfig?, templateContent?}`; tags normalized to `HtmlBasicTag {tag, attrs, children?, metadata?}` for user hooks then converted back with void-tag table.

### Decisive source
```ts
// alterAssetTagGroups: bridge user hook space onto html-rspack-plugin compilation hooks
hooks.alterAssetTagGroups.tapPromise(this.name, async (data) => {
  const extraData = getExtraDataByPlugin(data.plugin); if (!extraData) return data;
  if (!hasTitle(templateContent)) addTitleTag(headTags, data.plugin.options?.title);  // only when template lacks <title>
  if (favicon) await addFavicon({...});          // emits asset once via existence check in compilation.assets
  const [modified] = await context.hooks.modifyHTMLTags.callChain({environment: environment.name,
    args: [{headTags: headTags.map(formatBasicTag), bodyTags: ...}, {compiler, compilation, assetPrefix, filename, environment}]});
  Object.assign(data, {headTags: modified.headTags.map(fromBasicTag), ...});
  if (tagConfig) applyTagConfig(data, tagConfig, compilation.hash ?? '', entryName);
});
hooks.beforeEmit.tapPromise(this.name, async (data) => {
  const [modified] = await context.hooks.modifyHTML.callChain({environment, args: [data.html, {...}]});
  return {...data, html: modified};              // string-level last touch
});
```
```ts
// inline-chunk: rewrite tags at modifyHTMLTags; delete assets LATER at summarize stage
api.processAssets({ stage: 'summarize' }, ({compiler, compilation, environment}) => {
  const hasSourceMap = devtool !== 'hidden-source-map' && devtool !== false;
  for (const name of inlinedAssets) {
    if (hasSourceMap) {
      // Preserve source maps of inlined assets. Setting related.sourceMap to null prevents
      // deleteAsset from removing the source map file.
      compilation.updateAsset(name, asset, { related: { sourceMap: null } });
    }
    compilation.deleteAsset(name);
  }
});
// and updateSourceMappingURL rewrites the sourceMappingURL comment to the dist prefix after inlining.
```

**Flow:** per-entry options assembled in `pluginHtml` (template read once + existence cache, meta charset dedup against template content, chunksSortMode manual when dependOn present, scriptLoading module when output.module), registered in entryName order plus ONE shared RsbuildHtmlPlugin carrying the extraData map. crossorigin and nonce passes are modifyHTMLTags taps with `order:'post'` so they decorate every final tag (script/style/preload-as-script get nonce; script src / stylesheet link get crossorigin) regardless of earlier insertion. Tag priority sort: head base −2 vs body +2 shifted ±1 by append — deterministic placement for user-injected descriptors.

**Invariant:** modifyHTMLTags must run BEFORE applyTagConfig and both before modifyHTML; inlined assets must not disappear until AFTER html emission (summarize stage chosen explicitly because it is later than html-rspack-plugin emit).

**Probe:** `tests/htmlHelper.test.ts:5-19` pins hasTitle regex tolerance (whitespace/case variants); `e2e/cases/server/reload-html/index.test.ts:5-17+` pins template-change full reload interacting with liveReload.html flag. Inline-chunk source-map preservation has no direct test upstream — coverage caveat recorded from decisive comment.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "RsbuildHtmlPlugin applyTagConfig addFavicon modifyHTMLTags processAssets summarize", limit: 10 });
```

## Verdict
Adopt the four-phase tag pipeline, existence-checked favicon emit, deferred inline-deletion with source-map retention, and post-order security decoration. Adapt tag schema and hook names. Omit rsbuild's default-favicon discovery beyond noting publicDir probe order (ico/png/svg). Coverage caveat: e2e-cited behaviors; unit tests limited to helpers.
