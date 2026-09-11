<!-- capsule-v2 -->
# sourceMap devtool ladder + extract rule — why does prod js default to FALSE and legacy extract.js survive one more major?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the devtool decision table and the deprecated-but-honored extract.js shape.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/sourceMap.ts` — `getDevtool` 18–32, extract normalization 43–98 (legacy branch 58–77), applyExtractRule 100+; tests `packages/core/tests/sourceMap.test.ts` 12-case matrix.
**Signature:** `getDevtool(config): Rspack.DevTool`; `normalizeExtractOptions(extract?): ExtractRuleConfig | false`.
**Data Shape:** output.sourceMap: boolean | {js?, css?, extract?: true | {test,include,exclude}}.

### Decisive source
```ts
if (sourceMap === false) return false;
if (sourceMap === true) return isProd ? 'source-map' : 'cheap-module-source-map';
if (sourceMap.js === undefined) return isProd ? false : 'cheap-module-source-map';   // object form: prod opts OUT by default
return sourceMap.js;
```
```ts
const hasLegacyJs = 'js' in extract;
const hasFlatFields = ['test','include','exclude'].some((k) => extract[k] !== undefined);
if (extract.js === false) return false;                    // explicit opt-out survives merging
if (hasLegacyJs && !hasFlatFields) {                       // preserve deprecated shape when used alone
  const legacyJs = normalizeExtractTarget(extract.js);
  if (!legacyJs) return false;
  return { name: 'source-map-extract-js', test: JS_REGEX, target: legacyJs };
}
return { name: 'source-map-extract', test: test ?? JS_REGEX, target: {...} };   // new flat shape
```

**Flow:** extract rules add a loader that strips sourceMappingURL comments from matched outputs (maps stay on disk, comment removed → browser never fetches); include/exclude conditions pass through normalizeRuleConditionPath for Windows backslash forms. Devtools: cheap-module-source-map in dev for rebuild speed; full source-map only when explicitly true in prod.
**Invariant:** (1) object-form sourceMap WITHOUT js key means NO js maps in production — a porter copying the boolean semantics leaks giant sourcemaps; (2) `extract.js:false` must keep winning even beside flat fields or merged configs re-enable stripping; (3) the two rule NAMES differ ('source-map-extract-js' vs 'source-map-extract') — dedupe logic keys on them.
**Probe:** unit `packages/core/tests/sourceMap.test.ts:24/:30/:49/:63/:78/:96/:114/:136/:158/:180/:204/:228` (full extraction matrix incl. deprecated shapes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginSourceMap getDevtool normalizeExtractOptions applyExtractRule", limit: 8 });
```

## Verdict
Adopt the four-row devtool table and the dual-shape extract normalization with loud deprecation path. Adapt devtool strings to bundler. Omit CSS extract handling if host has no per-channel maps.
