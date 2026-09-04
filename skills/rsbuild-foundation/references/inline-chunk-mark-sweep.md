<!-- capsule-v2 -->
# Inline-chunk tag rewrite + deferred asset deletion — why is deletion a summarize-stage pass over a recorded set?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must keep the mark-then-sweep split, the source-map rescue, and the lazy Rust-JS bridge access pattern.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/inlineChunk.ts` — `updateSourceMappingURL` 18–46, `getMatchedAsset` 48–73, `getInlineTests` 75–119, processAssets summarize 245–284, modifyHTMLTags 286–318, per-env set 125–134.
**Signature:** `getInlineTests(config): {scriptTests, styleTests: (RegExp|fn)[]}`; `modifyHTMLTags` handler maps tags → inlined replacements while recording names.
**Data Shape:** `inlineAssetsByEnvironment: Map<envName, Set<assetName>>`; InlineChunkTest = RegExp | ({name,size})=>boolean.

### Decisive source
```ts
// Accessing an asset retrieves its Source through the Rust-JS bridge, so defer the lookup until the filename matches.
let asset; const matched = tests.some((test) => {
  if (isFunction(test)) { asset ??= assets[name]; if (!asset) return false; return test({ name, size: asset.size() }); }
  return test.exec(name);
});
return matched ? asset ?? assets[name] : undefined;
```
```ts
// summarize stage — AFTER html plugin emitted:
if (hasSourceMap) {
  // Setting `related.sourceMap` to `null` prevents `deleteAsset` from removing the source map file.
  compilation.updateAsset(name, asset, { related: { sourceMap: null } });
}
compilation.deleteAsset(name);
```
```ts
const prefix = addTrailingSlash(ensureAssetPrefix(config.output.distPath[type] || '', publicPath));
return source.replace(/# sourceMappingURL=/, `# sourceMappingURL=${prefix}`);   // only when devtool not inline
```

**Flow:** modifyHTMLTags rewrites `<script src>`→inline children and `<link rel=stylesheet>`→`<style>`, stripping src/href and recording names; enable gates: true|RegExp|fn|{enable:'auto'|bool,test} all coerce to prod-only unless 'always'; deletion waits for the summarize processAssets stage so the HTML plugin has already read the bytes. Inlined code's sourceMappingURL gets re-prefixed because relative resolution changed.
**Invariant:** (1) never delete during the tag pass — html-rspack-plugin still needs the assets in that same compilation; (2) without the related.sourceMap:null rescue, deleteAsset cascades and destroys the .map of code that is now IN the HTML; (3) function tests receive {name,size} — size access forces the bridge, so regex tests must stay lazy.
**Probe:** e2e `cases/assets/inline-query/index.test.ts:3`; `html/*` inline cases + snapshot suite `packages/core/tests/html.test.ts`. Coverage caveat: summarize-order verified by source comment + stage pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginInlineChunk getInlineTests getMatchedAsset updateSourceMappingURL", limit: 8 });
```

## Verdict
Adopt mark-on-tag-rewrite/sweep-at-summarize with source-map decoupling and lazy asset access. Adapt stage names to your bundler's processAssets ladder. Omit sourceMappingURL rewrite if your devtool never emits external maps.
