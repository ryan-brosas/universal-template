<!-- capsule-v2 -->
# Config merge semantics — which keys override instead of merge, and how do functions become chains?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must reproduce the exact precedence table (override paths, array concat, function chaining, boolean-beats-object) or merged configs will silently differ.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/mergeConfig.ts:OVERRIDE_PATHS` (4–26), `isOverridePath` (31–42), `merge` (44–95), `normalizeConfigStructure` (101–129), `mergeRsbuildConfig` (137–150).
**Signature:** `mergeRsbuildConfig<T = RsbuildConfig>(...configs: (T | undefined)[]): T`.
**Data Shape:** recursive `merge(x, y, path)`; path strings like `output.filename.*`, with `environments.` prefixes stripped by slicing twice (`key.split('.').slice(2).join('.')`) before lookup. Pre-normalization converts `output.copy` array → `{patterns}`, string `distPath` → `{root}`, scalar `watchFiles` → array — so downstream merge always sees canonical shapes.

### Decisive source
```ts
const OVERRIDE_PATHS = new Set([
  'performance.removeConsole', 'output.inlineScripts', 'output.inlineStyles',
  'output.cssModules.auto', 'output.manifest.filter', 'output.manifest.generate',
  'output.overrideBrowserslist', 'performance.printFileSize.exclude|include|total',
  'server.open', 'server.compress.filter', 'server.printUrls',
  'resolve.extensions', 'resolve.conditionNames', 'resolve.mainFields',
  'dev.writeToDisk', 'dev.client.overlay.errors', 'dev.client.overlay.runtime',
  'provider', 'customLogger',
]);
const isOverridePath = (key) => OVERRIDE_PATHS.has(key) || key.startsWith('output.filename.');

const merge = (x, y, path = '') => {
  if (isOverridePath(path)) return y ?? x;          // later config wins outright
  if (x === undefined) return isPlainObject(y) ? cloneDeep(y) : y;
  if (y === undefined) return isPlainObject(x) ? cloneDeep(x) : x;
  if (typeX === 'boolean' || typeY === 'boolean') return y;   // false kills object form
  if (isArrayX && isArrayY) return x.concat(y);     // arrays concatenate in order
  if (typeX === 'function' || typeY === 'function') return [x, y];  // functions CHAIN into arrays
  if (!isPlainObject(x) || !isPlainObject(y)) return y;       // scalars: last wins
  ...recurse union of keys...
};
```

**Flow:** inputs filtered for `undefined`, each run through `normalizeConfigStructure`, then pairwise reduced. The four-way policy per key kind: (1) override-listed dot-paths → `y ?? x`; (2) arrays on both sides concat preserving order (defaults first, user second — user rules run after built-ins); (3) any function present wraps BOTH sides into a `[x, y]` chained array so callback-style options compose instead of overwrite; (4) boolean vs anything → the boolean side wins entirely (e.g. `tools.htmlPlugin: {}` then `false` yields `false`). Plain objects deep-clone on isolation edges (`x===undefined` clones y; result never shares references with inputs).

**Invariant:** merging must never mutate either input and must never share nested object references across results — tests assert identity non-mutation explicitly; `undefined` values are always ignorable, never meaningful overrides.

**Probe:** `tests/mergeConfig.test.ts:5-11` pins false-replaces-empty-object; `:24-40` undefined-ignoring; `:50-69` string+array concat to `['./a.js','./b.js','./c.js']`; `:323-344` (`dev.writeToDisk` fn+fn) and `:346-379` (`overlay.errors`) pin override-not-chain for exactly those function-valued override paths; `:381-397` same for `server.compress.filter`; `:399-430` pins plugin class instances surviving merge uncloned; `:432-460+` pins environments-prefix stripping; `:590-618` all-undefined → `{}`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "mergeRsbuildConfig OVERRIDE_PATHS isOverridePath normalizeConfigStructure", limit: 10 });
```

## Verdict
Adopt the policy table + recursion as-is for layered tool configs; it is the single most-copied seam in this repo (fan-in 10 via hotspots). Adapt the specific key list to host option names. Omit rsbuild's deprecated-shape handling once ported targets are fixed. Coverage caveat: probes verified from on-disk rstest specs.
