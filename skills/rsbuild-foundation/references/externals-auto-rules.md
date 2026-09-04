<!-- capsule-v2 -->
# autoExternal → regex externals — why are deps compiled to `^pkg(?:$|[\\/\\\\])` and dropped on workers?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the dependency-list→externals-rule compiler, its exclusion ladder, and the worker-environment wipe.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/plugins/externals.ts` — dependencyTypes 10–15, defaults 17–22, `resolveAutoExternalOptions` 24–35, `escapeRegExp` 37, `matchAutoExternalExclude` 83–97, `composeAutoExternalRules` 99–140, `mergeExternals` 142–157, worker wipe 199–210.
**Signature:** `composeAutoExternalRules({autoExternal?, pkgJson?, userExternals?}): RegExp[] | undefined`.
**Data Shape:** merged PackageJson across N files per type; rules = RegExp[] anchored `^name(?:$|[/\\])`.

### Decisive source
```ts
const externals = dependencyTypes.reduce<string[]>((prev, type) => externalOptions[type] && isPlainObject(pkgJson[type]) ? prev.concat(Object.keys(pkgJson[type])) : prev, [])
  .filter((name) => !userExternalKeys.includes(name) &&
    (!excludeConditions || !matchAutoExternalExclude(name, excludeConditions)));
...
// Exclude dependencies and subpath imports, e.g. `react`, `react/jsx-runtime`.
return uniqueExternals.map((dep) => new RegExp(`^${escapeRegExp(dep)}(?:$|[/\\\\])`));
```
```ts
if (isWebWorker && config.externals) delete config.externals;   // onBeforeCreateCompiler: workers cannot access globals
```

**Flow:** default ON for dependencies+peerDependencies+optionalDependencies (devDependencies FALSE); user object-externals keys dedupe by name BEFORE regex generation; exclude accepts exact strings OR RegExp (stateful global/sticky regexes are CLONED before .test so user config's lastIndex is never mutated); final merge APPENDS auto rules after user externals (user wins by first-match). Warn-once flag (`hasWarnedReadPackageJsonFailed`) guards repeated read failures across rebuilds.
**Invariant:** (1) escapeRegExp before interpolation or scoped names (`@scope/pkg` → regex quantifier injection) silently break matching; (2) the `(?:$|[/\\])` tail is what distinguishes "externalize react" from "externalize react-native" — a bare `^react$` misses subpaths, a bare `^react` over-matches; (3) only PLAIN-OBJECT user externals can be deduped (arrays/functions opaque).
**Probe:** unit `packages/core/tests/externals.test.ts:14` ("should not enable autoExternal by default"), :36 compose table, :65 object-config case.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "pluginExternals composeAutoExternalRules matchAutoExternalExclude mergeExternals", limit: 8 });
```

## Verdict
Adopt dep-type-driven auto-externalization with escaped subpath-aware anchors, cloned-regexp excludes, append-order merging, and the post-config worker wipe. Adapt dependency-type toggles to your package manager layout. Omit pnpm path-walking in resolve.dedupe (separate seam).
