<!-- capsule-v2 -->
# SSR bundle runner — how are emitted bundles executed in Node with CJS/ESM requirers over vm?

**Source:** rsbuild MIT `main@ded92636403f823ab66bbd1acc1adc685a66fb97`; Codebase Memory `rsbuild`. **Question:** a porter must know the entry-chunk resolution rules (unique, non-CSS, isBundleOutput gate), the CJS compileFunction scope, and the ESM SourceTextModule requirements/fallbacks.

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/server/environment.ts:loadBundle` (11–68); `server/runner/index.ts:run`/BasicRunnerFactory (8–44); `server/runner/basic.ts:run/getRequire/getFile` (49–111); `server/runner/cjs.ts:CommonJsRunner` (17–120); `server/runner/esm.ts:EsmRunner` (9–102); `server/runner/asModule.ts` (17–54).
**Signature:** `run<T>({bundlePath, dist, compilerOptions, readFileSync, isBundleOutput}): Promise<T>`.
**Data Shape:** requirers registry `Map<'entry'|'cjs'|'esm'|'miss', RunnerRequirer>`; BasicRunnerFile `{path, content, subPath}`; esmCache `Map<path, SourceTextModule>`; EsmMode Unlinked|Evaluated.

### Decisive source
```ts
// factory: refuse to "run" browser bundles on the server
if (compilerOptions.target === 'web' || compilerOptions.target === 'webworker')
  throw new Error('... Not support run web resource in Rsbuild server');
// output.module && not .cjs → esm requirer, else cjs
this.requirers.set('entry', (dir, modulePath, context) => {
  const file = this.getFile(modulePath, dir);
  if (!file) return this.requirers.get('miss')!(dir, modulePath);
  if (outputModule && !file.path.endsWith('.cjs')) return this.requirers.get('esm')!(...);
  return this.requirers.get('cjs')!(...);
});
```
```ts
// CJS execution: vm.compileFunction with injected scope; require cache PRE-seeds before exec (cycle-safe)
const m = { exports: {} };
requireCache[file.path] = m;
const currentModuleScope = this.createModuleScope(this.getRequire(), m, file);
const fn = vm.compileFunction(file.content, Object.keys(currentModuleScope),
  { filename: file.path, importModuleDynamically: async (specifier) => dynamicImport(specifier) });
fn.call(m.exports, ...Object.values(currentModuleScope));
```
```ts
// ESM: requires --experimental-vm-modules; link() resolves via the SAME requirer wrapped by asModule
if (!vm.SourceTextModule) throw new Error('... needs add Node.js option --experimental-vm-modules.');
await esm.link(async (specifier, referencingModule) =>
  asModule(await _require(path.dirname(referencingModule.identifier), specifier, { esmMode: EsmMode.Unlinked }),
           referencingModule.context, true));
await esm.evaluate();
const ns = esm.namespace;
return ns.default && ns.default instanceof Promise ? ns.default : ns;   // TLA promise unwrapping
```
```ts
// asModule bridges CJS-shaped results into vm Module graph (default always present)
const normalized = normalizeModuleExports(moduleExports);      // primitives → {default}
const exports = [...new Set(['default', ...Object.keys(normalized)])];
new SyntheticModule(exports, () => {...setExport each...}, { context });
```

**Flow:** loadBundle derives entry chunk files from stats entrypoints (CSS filtered), enforces single-file entries, computes allChunkFiles for `isBundleOutput`, executes. getFile treats array-require as a synthesized virtual `.array-require.js`; non-bundle paths fall through to 'miss' requirer which resolves via real Node require (stripping `node:` prefix quirk). Global context deliberately unrefs setTimeout so SSR code cannot hold the dev process open.

**Invariant:** require-cache seeding BEFORE execution is what makes circular CJS modules behave like Node; every vm-executed file must come from the bundle output set or it escapes to host resolution.

**Probe:** `e2e/cases/server/ssr-load-bundle-external/index.test.ts:10-29` pins default-import type parity with native import; `e2e/cases/server/ssr-type-module` and `load-bundle-cjs` cases exercise both requirers. No unit tests for runner classes — coverage caveat recorded (deterministic source read).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "rsbuild", query: "EsmRunner CommonJsRunner BasicRunner asModule loadBundle createEsmRequirer", limit: 10 });
```

## Verdict
Adopt requirer-registry + preseeded cache + SyntheticModule bridging for executing emitted bundles server-side. Adapt target refusal list and TLA handling to host runtime versions. Omit rsbuild's array-require helper unless porting test-tooling too. Coverage caveat: e2e-cited only.
