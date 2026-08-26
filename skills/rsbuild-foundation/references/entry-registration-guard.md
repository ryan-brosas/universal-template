<!-- capsule-v2 -->
# Entry registration + missing-entry guard — why does core-js become a VIRTUAL pre-entry and MF apps get an empty entry?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce pre-entry ordering (preEntry → core-js → user), the html-key strip, and the module-federation entry exemption.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/entry.ts` — addEntry with html-strip 16–23, injection order 25–31, onBeforeCreateCompiler post-order guard 36–65.
**Signature:** `addEntry(item: string | RsbuildEntryDescription)`; virtual modules via `createVirtualModule('import "core-js";')`.
**Data Shape:** source.entry: Record<name, string | desc[]>, desc may carry UI-only `html` key.

### Decisive source
```ts
const injectCoreJsEntry = config.output.polyfill === 'entry' && !isServer;
...
preEntry.forEach(addEntry);                       // user pre-entries FIRST
if (injectCoreJsEntry) addEntry(createVirtualModule('import "core-js";'));   // polyfill before app code
castArray(entry[entryName]).forEach(addEntry);
```
```ts
// Allow entry to be left empty when module federation is enabled:
const hasModuleFederation = bundlerConfigs.some(({ plugins }) => plugins?.some(isModuleFederationPlugin));
if (hasModuleFederation) { bundlerConfigs.forEach((config) => { config.entry = {}; }); return; }
throw new Error('Could not find any entry module, please make sure that src/index.(ts|js|...) exists, ...');
```

**Flow:** order is load-bearing: polyfills and preEntry scripts execute before ANY application module. The `html` key in a description object is rsbuild-UI metadata and MUST be destructured out before chain.entry().add or rspack rejects the unknown key. The missing-entry check runs at POST order so other plugins had their chance to synthesize entries first.
**Invariant:** (1) entry ORDER within a name defines module execution order — reordering preEntry breaks polyfill-dependent app code; (2) MF detection runs on CONSTRUCTOR NAME ('ModuleFederationPlugin') because the plugin class isn't importable here; (3) setting entry={} explicitly (not just leaving undefined) is what silences downstream validation.
**Probe:** unit snapshot `packages/core/tests/entry.test.ts` (virtual-module + pre-entry ordering).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginEntry createVirtualModule injectCoreJsEntry ModuleFederationPlugin", limit: 8 });
```

## Verdict
Adopt ordered injection with virtual polyfill modules and the MF empty-entry carve-out. Adapt virtual-module encoding to bundler. Omit html-key handling if host descriptions lack UI keys.
