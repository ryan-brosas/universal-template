<!-- capsule-v2 -->
# VM code-cache rejection fallback — how does the ESM executor recover when V8 rejects a module's cached compile buffer?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@c3ba16b3`); Codebase Memory `vitest`. **Question:** When V8 rejects cachedData at SourceTextModule construction (e.g. V8 flags changed at runtime), what must a porter do to avoid crashing every later test file sharing the cache?

## Rejection-caught construct ladder
**Path/Symbol:** `packages/vitest/src/runtime/vm/esm-executor.ts:createSourceTextModule` (:162–201), catch arm :184–192; cache twin `CodeCache.delete` in `runtime/vm/code-cache.ts` (:49–51).
**Signature:** `private createSourceTextModule(fileURL: string, code: string): VMSourceTextModule`.
**Data Shape:** `CodeCache.get(identifier, source)` returns the stored `Buffer | undefined` ONLY when the entry's guarded exact source text matches; `ERR_VM_MODULE_CACHED_DATA_REJECTED` is thrown by `new SourceTextModule(code, { ...options, cachedData })` itself (unlike `vm.Script`, which constructs fine and sets `cachedDataRejected` afterwards).

### Decisive source
```ts
let m: VMSourceTextModule | undefined
if (cachedData) {
  try {
    m = new SourceTextModule(code, { ...options, cachedData })
  }
  catch (error: any) {
    // unlike vm.Script, a module throws when V8 rejects the cache (e.g. the
    // V8 flags changed at runtime): compile from source instead
    if (error?.code !== 'ERR_VM_MODULE_CACHED_DATA_REJECTED') {
      throw error
    }
    codeCache!.delete(fileURL)
    cachedData = undefined
  }
}
m ??= new SourceTextModule(code, options)
// the code cache of a SourceTextModule must be created before evaluation
if (!cachedData) {
  const created = m
  codeCache?.store(fileURL, code, () => created.createCachedData())
}
```

**Flow:** `get` (exact-source-guarded) → if a buffer exists, TRY constructing with it → rejection error deletes the dead entry and falls through to plain construction; ANY other error rethrows untouched → fresh modules register a lazy `createCachedData()` producer via `store`, which records a failed produce as an empty entry so it is never retried per context.
**Invariant:** (1) Only the specific `ERR_VM_MODULE_CACHED_DATA_REJECTED` code takes the fallback — swallowing other constructor errors hides real syntax/host bugs. (2) The rejected identifier MUST be deleted from the worker-wide cache, else every subsequent fresh-context executor replays the same poisoned buffer. (3) New cachedData is produced strictly BEFORE evaluation. A porter who ports the `vm.Script` mental model here (check a post-construction `cachedDataRejected` flag) ships a crash: modules THROW instead. The CJS twin really does use the flag form (`commonjs-executor.ts:171–173`, `script.cachedDataRejected` → delete) — the asymmetry is the point.
**Probe:** `test/unit/test/vm-code-cache.test.ts` — six `test()` blocks pin exact-source-only reads, produce-once, replace-entry-on-changed-source, failed-produce-recorded-once, and delete; e2e `test/e2e/test/vm-threads.test.ts` `"survives a runtime V8 flag change from the %s"` runs the 4-way `{vmThreads,vmForks} × {context, worker realm}` matrix asserting clean stderr/exit across three sequential test files. Verified on disk: 6 unit tests, 1 e2e describe-line hit.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "createSourceTextModule ERR_VM_MODULE_CACHED_DATA_REJECTED CodeCache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the try/catch-with-error-code fallback plus delete-then-recompile and the pre-evaluation store rule. Adapt the error-code check to your host's vm API surface (flag-based rejection needs the CJS-style post-check instead). Omit nothing — skipping the fallback turns a runtime flag change into a hard crash shared by every test file on the worker.
