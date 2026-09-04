<!-- capsule-v2 -->
# Transform pipeline loaders — how does `api.transform` reach module content without one loader per transform, and when do source maps survive?

**Source:** rsbuild MIT `main@2bcf61c67072537c68f93d6700d7ac20a0f3f8f5`; Codebase Memory `rsbuild`. **Question:** a porter adding a user-facing transform hook must know the registry indirection that keeps N transforms on ONE loader file, the no-op fallbacks, and exactly which result shapes preserve incoming source maps.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/loader/transformLoader.ts:transformLoader` (23–79), `mergeSourceMap` (10–21); `packages/core/src/loader/transformRawLoader.ts` (1–6); registry side `compiler.__rsbuildTransformer[id]` minted by `plugin-api-surface`'s `api.transform`.
**Signature:** `transformLoader: LoaderDefinition<TransformLoaderOptions>` with options `{ id: string; getEnvironment: () => EnvironmentContext }`; handler receives `{ code, context, resource, resourcePath, resourceQuery, environment, addDependency, addMissingDependency, addContextDependency, emitFile, importModule, resolve }`.
**Data Shape:** transform handlers live in a symbol-keyed map on the compiler; the rule's loader options carry only `{id, getEnvironment}`. Result may be `null | undefined | string | Buffer | { code, map? }`.

### Decisive source
```ts
const transform = this._compiler?.__rsbuildTransformer?.[transformId];
if (!transform) { callback(null, source, map); return; }        // missing id/registry → pass through untouched

if (result === null || result === undefined) {
  callback(null, source, map); return;                          // void result = "not mine"
}
if (typeof result === 'string' || Buffer.isBuffer(result)) {
  callback(null, result, map); return;                          // plain code keeps INCOMING map
}
const mergedMap =
  map && result.map
    ? await mergeSourceMap(map, result.map)                     // remapping([generated, original], () => null)
    : (result.map ?? map);                                      // either-side-only map wins as-is
callback(null, result.code, mergedMap);
```
```ts
// transformRawLoader.ts — the ENTIRE raw twin:
import transform from './transformLoader';
export default transform;
// make the loader to receive raw Buffer
export const raw = true;
```

**Flow:** plugin setup mints `id`, stores handler in `__rsbuildTransformer`, taps `modifyBundlerChain` to add a rule whose `.use()` points at `LOADER_PATH/transformLoader.mjs` (`transformRawLoader.mjs` when `raw: true`) with `{id, getEnvironment}` options → at transform time the generic loader looks the handler up per-module, invokes it with resource parts + environment context, then maps the result shape onto `callback(code, map)`.

**Invariant:** a transform that returns nothing, or an id missing from the registry, MUST fall back to `callback(null, source, map)` — never drop or re-encode content. Source maps are only REWRITTEN when both sides exist; a Buffer/string result preserves the incoming chain verbatim.

**Probe:** `packages/core/tests/__snapshots__/nodeAddons.test.ts.snap` pins the generated rule to `loader: "<ROOT>/packages/core/src/transformRawLoader.mjs"` with `options {id: "rsbuild-transform-0", getEnvironment: [Function]}` — proving raw transforms share the same loader identity plus the `raw` export. Source pins: `export const raw = true` (transformRawLoader.ts:6), no-op fallbacks at transformLoader.ts:28–37/55–58.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "transformLoader mergeSourceMap rsbuildTransformer getEnvironment", limit: 10 });
```
Executed post-reindex: `transformLoader` resolves in `packages/core/src/loader/transformLoader.ts`; nodeAddons snapshot corroborates the .mjs twin naming.

## Verdict
Adopt the single-generic-loader + symbol-keyed handler registry (it is what lets a framework expose arbitrary code transforms without loader-per-plugin churn) and the three-branch result mapping with remapping-based merge. Adapt option plumbing to your bundler's loader-options API and the registry home (rsbuild hangs it off `compiler.__rsbuildTransformer`). Omit the `.mjs` build-step duality if your host compiles TS loaders natively. Coverage caveat: no dedicated unit suite for transformLoader.ts itself; behavior pinned via nodeAddons snapshot + direct source read at pin.
