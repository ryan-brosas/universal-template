<!-- capsule-v2 -->
# CJS cross-context script cache — how are CommonJS modules compiled once and evaluated in every vm context without leaking per-context state?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b3`); Codebase Memory `vitest`. **Question:** What exactly is shared versus per-context when CJS files run inside `pool: 'vmThreads'`/`'vmForks'`, and where do the code-cache read/write points sit?

## Module-level Script cache + per-context evaluation
**Path/Symbol:** `packages/vitest/src/runtime/vm/commonjs-executor.ts:cjsScriptCache` (:48), `_compile` (:146–191); rejection arm :171–173; store-in-finally :189.
**Signature:** `const cjsScriptCache = new Map<string, vm.Script>()`; `_compile(code: string, filename: string): unknown`.
**Data Shape:** Key = filename; value = compiled `vm.Script`. The executor class itself is instantiated PER test file (fresh context each), but `cjsScriptCache` is MODULE-level — shared by every fresh-context executor on the worker. Compiled scripts carry no per-context state because both callbacks passed into `vm.Script` are static: `importModuleDynamically: activeImportModuleDynamically` resolves the owning executor at CALL time.

### Decisive source
```ts
let script = cjsScriptCache.get(filename)
if (!script) {
  const cachedData = codeCache?.get(filename, cjsModule)
  try {
    script = new vm.Script(cjsModule, {
      filename,
      cachedData,
      importModuleDynamically: activeImportModuleDynamically,
    } as any)
  }
  catch (error) { /* SyntaxError + .js → CjsParseError ESM fallback */ }
  if (cachedData && script.cachedDataRejected) {
    codeCache!.delete(filename)
  }
  cjsScriptCache.set(filename, script)
}
const fn = script.runInContext(executor.context)
...
finally {
  this.loaded = true
  // store after execution so the code cache carries the compiled
  // module body, not only the lazily-parsed wrapper
  codeCache?.store(filename, cjsModule, () => script.createCachedData())
}
```

**Flow:** `_compile` wraps source in the CJS wrapper → cache hit skips compilation entirely (only `runInNewContext`-equivalent work repeats per context) → miss consults CodeCache (source-guarded buffer) → `vm.Script` CONSTRUCTS even with rejected data (flag check afterwards — the mirror image of the ESM executor's throw form) and deletes dead entries → `runInContext(executor.context)` yields the wrapped fn → module body executes with `(exports, require, module, filename, __dirname)` → finally-block stores the produced cachedData AFTER execution.
**Invariant:** (1) Only EVALUATION is per-context; compilation is worker-wide — a porter who moves the Script construction inside a per-context structure silently loses the entire speedup. (2) Rejection detection here is the POST-construction boolean `script.cachedDataRejected`, never a catch. (3) Store must sit AFTER execution (in-source comment): caching the pre-evaluation compile captures only the lazily-parsed wrapper. (4) No invalidation exists for this Map BY DESIGN — watch-mode reruns destroy the whole worker (in-source comment). A porter who adds TTL/invalidation logic to the Script map ports behavior the repo deliberately does not have.
**Probe:** `grep -c 'cachedDataRejected' packages/vitest/src/runtime/vm/commonjs-executor.ts` = 1 (:171 sole flag site); unit twin for the shared buffer contract: `test/unit/test/vm-code-cache.test.ts` six tests. Both verified on disk at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "cjsScriptCache _compile runInContext cachedDataRejected", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt compile-once-per-worker / evaluate-per-context with static callbacks and the post-execution store point. Adapt the wrapper shape and extension handling to your host's loader. Omit invalidation machinery entirely unless your host keeps workers alive across watched changes (Vitest does not).
