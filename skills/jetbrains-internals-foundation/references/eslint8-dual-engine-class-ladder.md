<!-- capsule-v2 -->
# ESLint 8 dual-engine class ladder — how does ONE shim class serve eslint 8 AND eslint 9+ when the meaning of the `.ESLint` export flips between them?

**Source:** JetBrains IDE installed build `WebStorm 262.9437.145`; Codebase Memory `jetbrains-webstorm`. **Question:** above.

## Dual-engine constructor with unsupported-api cross-load
**Path/Symbol:** `plugins/javascript-eslint/languageService/eslint/bin/eslint8-plugin.js`:`ESLint8Plugin` (:54-97), engine pick in `invokeESLint` (:169, :191).
**Signature:** `new ESLint8Plugin(state)` with `state = { linterPackageVersion: string, eslintPackagePath: string, packageJsonPath: string, includeSourceText: boolean, additionalRootDirectory?: string }`.
**Data Shape:** two engine slots `this.FlatESLint` / `this.LegacyESLint` plus `this.libOptions`, all nullable; per-request boolean `requestArguments.flatConfig` decides which slot is instantiated.

### Decisive source
```js
var isESLint8 = state.linterPackageVersion.substring(0, 2) == "8.";
var defaultESLint = requireInContext(normalizePath(state.eslintPackagePath), state.packageJsonPath).ESLint;
if (isESLint8) { this.LegacyESLint = defaultESLint; }
else           { this.FlatESLint   = defaultESLint; }   // 9+: .ESLint IS the flat engine
…
this.FlatESLint   = requireInContext("../lib/unsupported-api", apiJsPath).FlatESLint;   // 8.x only (try/catch → null)
this.LegacyESLint = requireInContext("../lib/unsupported-api", apiJsPath).LegacyESLint; // 9+ fallback (try/catch → null)
…
usingFlatConfig = requestArguments.flatConfig && this.FlatESLint instanceof Function;
eslint = usingFlatConfig ? new this.FlatESLint(options) : new this.LegacyESLint(options);
```
(apiJsPath = `requireResolveInContext(eslintPackagePath)`; the `../lib/options` and `../lib/unsupported-api` requires are RELATIVE TO that resolved api.js path, so they always load from the USER's install.)

**Flow:** version prefix sniff assigns the default `.ESLint` export to one slot → resolve api.js path → try to fill the OPPOSITE slot from `unsupported-api` (each failure degrades to `null`) → at request time the JVM-sent `flatConfig` bit AND a live `instanceof Function` probe together select the engine.
**Invariant:** (1) the sniff is deliberately NON-semver — `substring(0,2) == "8."` only, no parsing, tolerant of odd version strings; (2) every optional capability must degrade to `null` and be re-probed (`instanceof Function`), never assumed — an outer catch swallows even api.js resolution failure leaving just the default engine; (3) sibling internals load relative to the RESOLVED user package, never the shim's own directory.
**Probe:** `node --check eslint8-plugin.js` → OK (executed); `grep -c "unsupported-api"` = 2, `grep -cF 'substring(0, 2) == "8."'"` = 1 (executed). Coverage: no_recorded_issue.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "jetbrains-webstorm", name_pattern: "^ESLint8Plugin$", limit: 5 });
// hit: …bin.eslint8-plugin.ESLint8Plugin @ eslint8-plugin.js:54-97, single caller eslint-plugin-provider:1
```

## Verdict
Adopt the dual-slot + degrade-to-null + live-probe pattern for any adapter spanning a third-party library's API flip (the flip point here is exactly major 9). Adapt the sniff to your supported range — keep it prefix-based if you want tolerance for prerelease strings. Omit the `unsupported-api` deep-internal dependency only if your host range starts at the flip major; otherwise keep it best-effort behind try/catch like this source does.
