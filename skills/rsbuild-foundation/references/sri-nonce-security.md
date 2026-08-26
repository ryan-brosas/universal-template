<!-- capsule-v2 -->
# SRI + nonce security pairing — why does SRI force crossOriginLoading and nonce inject via anonymous EntryPlugin?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce both CSP-adjacent mechanisms and their enable gates.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/sri.ts` whole 6–40; `packages/core/src/plugins/nonce.ts` whole 6–65 (EntryPlugin injection 30–37, tag ladder 40–63).
**Signature:** sri: modifyBundlerChain handler keyed on security.sri; nonce: onAfterCreateCompiler + modifyHTMLTags(order:'post').
**Data Shape:** security.sri {enable:'auto'|boolean, algorithm?: SriAlgorithm|[]}; security.nonce: string | per-env.

### Decisive source
```ts
const enable = sri.enable === 'auto' ? config.mode === 'production' : sri.enable;
// SRI requires a cross-origin policy:
const crossorigin = chain.output.get('crossOriginLoading');
if (crossorigin === false || crossorigin === undefined) chain.output.crossOriginLoading('anonymous');
if (config.html.implementation === 'js' && config.tools.htmlPlugin !== false)
  pluginOptions.htmlPlugin = path.join(COMPILED_PATH, 'html-rspack-plugin/index.js');   // hook the JS html impl too
```
```ts
const injectCode = createVirtualModule(`import.meta.rspackNonce = ${JSON.stringify(nonce)};`);
new rspack.EntryPlugin(compiler.context, injectCode, { name: undefined }).apply(compiler);  // EVERY entry, no name
...
if (tag.tag==='script' || tag.tag==='style' || (tag.tag==='link' && tag.attrs?.rel==='preload' && tag.attrs?.as==='script'))
  tag.attrs.nonce = nonce;    // order:'post' so user tag edits are already applied
```

**Flow:** SRI hashes emitted files and stamps integrity attributes through the html plugin's hooks — without crossorigin=anonymous the browser refuses same-site-CORS-less comparisons. Nonce travels two paths: runtime globals via a nameless virtual-module entry (import.meta.rspackNonce) and static HTML attributes via post-order tag mutation covering scripts, styles, and script-preload links only.
**Invariant:** (1) 'auto' means PROD-only for both features — dev integrity/nonce churn breaks HMR; (2) nonce EntryPlugin uses name:undefined so shared chunks aren't re-created per named entry; (3) the preload+as=script link must be included or CSP blocks the fetched-but-not-yet-executed module.
**Probe:** e2e `cases/security/sri-basic/index.test.ts:4/:25` (integrity regex in build / absent in dev), `security/nonce-basic/index.test.ts:4/:12` (script+style nonce attrs, env-scoped nonce).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginSri pluginNonce SubresourceIntegrityPlugin EntryPlugin createVirtualModule", limit: 8 });
```

## Verdict
Adopt auto-prod gating, crossorigin preconditions, dual-path nonce delivery, and post-order tag stamping. Adapt hash algorithm defaults and nonce transport to host CSP policy. Omit htmlPlugin JS-impl wiring if host has a single html plugin.
