<!-- capsule-v2 -->
# PostCSS config discovery cache + function-options wrapper — why is postcssrc cached per root and wrapped twice?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must keep per-build config isolation AND merge user `tools.postcss` function results with discovered postcssrc without double-initializing plugins.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/css.ts` — `clonePostCSSConfig` 93–96, `loadUserPostcssrc` 103–127, `getPostcssLoaderOptions` 132–225 (wrapper 193–221), `isPostcssPluginCreator` 129–130.
**Signature:** `loadUserPostcssrc(root, cache: Map<string, PostCSSOptions|Promise<PostCSSOptions>>): Promise<PostCSSOptions>`; `postcssOptionsWrapper(loaderContext): PostCSSOptions` with `.config = false`.
**Data Shape:** cache stores raw promise then resolved object; EVERY returned value passes through shallow clone with copied `plugins` array.

### Decisive source
```ts
const clonePostCSSConfig = (config) => ({ ...config, plugins: config.plugins ? [...config.plugins] : undefined });

const promise = postcssrc({}, root).catch((err) => {
  if ((err as Error).message?.includes('No PostCSS Config found')) return {};   // fail-open to empty
  throw err;
});
postcssrcCache.set(root, promise);            // cache the PROMISE first: concurrent builds share one discovery
return promise.then((config) => { postcssrcCache.set(root, config); return clonePostCSSConfig(config); });
```
```ts
const mergedOptions = { ...userOptions, ...options, plugins: [...(userOptions.plugins||[]), ...(options.plugins||[])] };
return updatePostcssOptions(mergedOptions);
// updatePostcssOptions: append extraPlugins, THEN coerce creators:
options.plugins = options.plugins.map((p) => isPostcssPluginCreator(p) ? p() : p);  // #3618 double-init fix
options.config = false;                       // external config already loaded — disable loader-side lookup
```

**Flow:** discover once per root (promise-cached) → clone on every read so environment A mutating plugins can't leak into environment B → user function options spread OVER discovered options but plugins CONCATENATE (discovered first, function's second) → extraPlugins pushed last → factory-function plugins invoked once up front → `config:false` stamped so postcss-loader never re-runs its own cosmiconfig.
**Invariant:** (1) clone-before-use or cross-environment plugin mutation corrupts sibling builds; (2) plugin creator functions MUST be invoked before passing to postcss-loader or each file re-invokes them (#3618); (3) `postcssOptionsWrapper.config = false` must be set on the FUNCTION object itself (215) — the property lives outside the returned options.
**Probe:** e2e `e2e/cases/css/postcss-add-plugins/index.test.ts:4` (addPlugins order lands in compiled CSS); `css/postcss-config-ts`, `postcss-function-options` cases pin discovery + function forms.
**Coverage caveat:** cache/promise mechanics verified by source read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "loadUserPostcssrc getPostcssLoaderOptions postcssrcCache", limit: 8 });
```

## Verdict
Adopt promise-then-value caching with defensive cloning, concat-not-overwrite plugin merging, eager creator invocation, and disabled secondary config lookup. Adapt error-message sniffing ('No PostCSS Config found') to your config loader's wording.
