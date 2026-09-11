<!-- capsule-v2 -->
# v8 setFlagsFromString cache reset — how do runtime V8 flag changes avoid poisoning the worker-wide code cache?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b3`); Codebase Memory `vitest`. **Question:** When test code inside the vm context calls `v8.setFlagsFromString`, why doesn't every already-compiled code-cache buffer become a rejection bomb, and what must a porter replicate?

## Prototype-cloned v8 module wrapper
**Path/Symbol:** `packages/vitest/src/runtime/vm/code-cache.ts:createV8ModuleWithCacheReset` (:62–72); injection site `runtime/vm/commonjs-executor.ts:requireCoreModule` v8 arm (:517–522).
**Signature:** `function createV8ModuleWithCacheReset<T extends { setFlagsFromString: (flags: string) => void }>(v8: T, codeCache: CodeCache): T`.
**Data Shape:** Input is the host-realm `node:v8` exports object; output is a NEW object — `Object.create(Object.getPrototypeOf(v8), Object.getOwnPropertyDescriptors(v8))` — sharing prototype and all own descriptors, with ONLY `setFlagsFromString` replaced by an owning `function` that delegates to the original then clears the whole cache. The patched object is cached per executor in `builtinCache['v8']`, so one reset-wrapped instance serves all `require('v8')` callers in that context.

### Decisive source
```ts
export function createV8ModuleWithCacheReset<T extends { setFlagsFromString: (flags: string) => void }>(
  v8: T,
  codeCache: CodeCache,
): T {
  const patched = Object.create(Object.getPrototypeOf(v8), Object.getOwnPropertyDescriptors(v8)) as T
  patched.setFlagsFromString = function setFlagsFromString(flags: string): void {
    v8.setFlagsFromString(flags)
    codeCache.clear()
  }
  return patched
}
```
```ts
// commonjs-executor.ts — only when this executor owns a codeCache
if (normalized === 'v8' && this.codeCache) {
  const module = new this.Module('/v8.js')
  module.exports = createV8ModuleWithCacheReset(moduleExports, this.codeCache)
  this.builtinCache[normalized] = module
  return module.exports
}
```

**Flow:** Test code requires `node:v8` (or `require('v8')`) inside the vm context → `requireCoreModule` intercepts the normalized id BEFORE the generic builtin path → wraps the host-realm exports in the clone → any in-context `setFlagsFromString('--flag')` call first applies the flags to real V8 then empties every entry of the worker-wide CodeCache in one `clear()` → subsequent compiles run flag-faithfully and re-store fresh buffers.
**Invariant:** Changing V8 flags invalidates EVERY code cache produced so far (the in-source doc comment is the contract) — clearing must be TOTAL (`entries.clear()`), not per-identifier. The wrapper must delegate to the ORIGINAL `setFlagsFromString` (bound to the host realm), never to the clone. The interception is gated on `this.codeCache` existing: executors without a cache hand back raw exports. A porter who skips this ships the e2e failure mode #11031 fixed: three sequential files, one flips flags mid-run, later files crash on rejected cachedData.
**Probe:** `test/e2e/test/vm-threads.test.ts` — `"survives a runtime V8 flag change from the %s"` over `[vmThreads|vmForks] × [context|worker realm]`: inline tests import a padded `esm-dep` (200 comment lines "so V8 emits a code cache"), flip `--expose-gc` from either the context's `node:v8` or the worker realm via `process.getBuiltinModule('node:v8')`, and assert empty stderr + exit 0 across a/b/c test files. Verified on disk: describe-line ×1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "createV8ModuleWithCacheReset setFlagsFromString requireCoreModule", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrap-on-intercept + clear-all contract for any host that shares compiled-code buffers across execution contexts where tests can touch V8 flags. Adapt which builtin ids you intercept (here exactly `v8`/`node:v8`) and how your realm bridges the host exports. Omit the prototype-clone mechanics if your host can monkey-patch safely — but keep the delegation-to-original + total-clear semantics.
