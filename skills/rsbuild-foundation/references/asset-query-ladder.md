<!-- capsule-v2 -->
# Static asset oneOf ladder — why do ?url/?inline/?raw/type:text outrank the size-gated default?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the five-way asset rule order and the emit=false generator propagation.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/asset.ts` — `chainStaticAssetRule` 18–66, `getRegExpForExts` 68–79, per-type rules 126–142, JSON rule 146–150, global emit-off 155–157, assetsInclude 160–173.
**Signature:** `getRegExpForExts(exts): RegExp`; `createAssetRule(assetType, exts, emit)`.
**Data Shape:** oneOf ids `${type}-asset-url|-inline|-text|-raw|${type}`; dataUriLimit numeric-or-per-type record.

### Decisive source
```ts
rule.oneOf(`${assetType}-asset-url`).type('asset/resource').resourceQuery(URL_QUERY_REGEX)...   // ?url forces emit-file
rule.oneOf(`${assetType}-asset-inline`).type('asset/inline').resourceQuery(INLINE_QUERY_REGEX); // ?inline forces base64
rule.oneOf(`${assetType}-asset-text`).type('asset/source').with({ type: 'text' });             // import attributes
rule.oneOf(`${assetType}-asset-raw`).type('asset/source').resourceQuery(RAW_QUERY_REGEX);       // ?raw
rule.oneOf(`${assetType}-asset`).type('asset')
  .parser({ dataUrlCondition: { maxSize } });                                                   // SIZE decides
```
```ts
if (!emitAssets) chain.module.generator.merge({ 'asset/resource': { emit: false } });
```
```ts
new RegExp(normalizedExts.length === 1 ? `\\.${matcher}$` : `\\.(?:${matcher})$`, 'i');
```

**Flow:** query/attribute oneOfs precede the fallback so explicit intent always wins; the final branch delegates inline-vs-file to Rspack's dataUrlCondition using output.dataUriLimit (number shared, or per-type entry). Filename templates get distDir posix-joined (function forms wrapped). When emitAssets=false (e.g. SSR build where the web build owns assets) every asset/resource generator emits nothing instead of removing rules — URLs still resolve.
**Invariant:** (1) oneOf ORDER is the contract; putting `-asset` first would swallow every `?url` request; (2) `getRegExpForExts` non-capturing group only when multiple extensions (single-ext regexes stay capture-free for replace() callers); (3) emit-off rides the GENERATOR not rule removal so module graph and URL computation stay intact.
**Probe:** unit `packages/core/tests/asset.test.ts` (snapshot table per type); e2e `cases/assets/inline-query/index.test.ts:3` (?inline), `assets/url-query` / `css/raw-query` families pin each query branch.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginAsset chainStaticAssetRule getRegExpForExts dataUriLimit emitAssets", limit: 8 });
```

## Verdict
Adopt intent-first oneOf ordering with size-gated fallback and generator-level emit suppression. Adapt extension tables and dataUriLimit defaults to host. Omit JSON special-casing if your bundler lacks a built-in JSON rule to shadow.
