<!-- capsule-v2 -->
# Glob-cache side-effects — why must test-file matching go through the project's cached list, and what breaks if you re-glob or bypass it?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** How does "is this path a test file?" stay consistent between initial globbing, watcher `add` events, and rerun filtering — and who is allowed to mutate the cache?

## matchesTestGlob + testFilesList cache
**Path/Symbol:** `packages/vitest/src/node/project.ts:TestProject` — `globAllTestFiles` (:316–331), `_removeCachedTestFile` (:342–346), `_isCachedTestFile` (:352–354), `matchesTestGlob` (:372–395), `markTestFile` (:337–339), `filterFiles` (:397–423).
**Signature:** `public matchesTestGlob(moduleId: string, source?: () => string): boolean`; `/** @internal */ _isCachedTestFile(testPath: string): boolean`.
**Data Shape:** `testFilesList: string[] | null` — null until first glob; populated by `globProjectTestFiles` AND lazily by `matchesTestGlob` hits. `typecheckFilesList` mirrors it for typecheck includes. Filters are lowercase substring-or-absolute-prefix matches relative to `config.dir || root`.

### Decisive source
```ts
public matchesTestGlob(moduleId: string, source?: () => string): boolean {
  if (this._isCachedTestFile(moduleId)) return true        // cache hit short-circuits I/O
  const relativeId = relative(this.config.dir || this.config.root, moduleId)
  if (pm.isMatch(relativeId, this.config.exclude)) return false   // exclude BEFORE include
  if (pm.isMatch(relativeId, this.config.include)) {
    this.markTestFile(moduleId)                            // SIDE EFFECT: grows the cache
    return true
  }
  if (this.config.includeSource?.length && pm.isMatch(relativeId, this.config.includeSource)) {
    const code = source?.() || readFileSync(moduleId, 'utf-8')   // lazy read via memo closure
    if (isInSourceTestCode(code)) {                        // in-source tests need content proof
      this.markTestFile(moduleId)
      return true
    }
  }
  return false
}
// deletion path (watcher unlink) keeps cache coherent:
_removeCachedTestFile(testPath: string) { this.testFilesList = this.testFilesList?.filter(f => f !== testPath) }
```

**Flow:** first run globs include/exclude into `testFilesList` → every later membership question (watcher `add`, rerun filtering, `handleFileChanged` fallback) asks `_isCachedTestFile` FIRST → a positive match from full globbing marks the file so subsequent asks are O(1) → file deleted ⇒ watcher calls `_removeCachedTestFile` on every project before dropping state. `globAllTestFiles` returns the cache wholesale when non-null.
**Invariant:** the cache is BOTH a performance memo AND the authority for "was this file part of the last collection" — recomputing per-event with fresh globbing would make watch behavior depend on disk races and would resurrect files that were excluded at startup. Exclude-before-include ordering is load-bearing. The `source?: () => string` thunk exists ONLY to avoid reading a file twice (watcher passes a memoizing closure: `() => (fileContent ??= readFileSync(id, 'utf-8'))`). `filterFiles` lowercases both sides but keeps absolute-path prefix matching case-sensitive-by-startsWith semantics on the ORIGINAL entry.
**Probe:** `test/e2e/test/watch/file-watching.test.ts` 'adding a new test file triggers re-run' (:160–181): a created file matching the glob is picked up via `matchesTestGlob` during `onFileCreate` without a re-glob of the whole tree; rename scenario :183–224 pins removal (`Test removed` then pattern no longer matches).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "matchesTestGlob", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt cache-as-authority for test-file membership with explicit removal-on-delete; adapt glob engine (picomatch) and in-source detection regex to your host. Omit `includeSource` content sniffing unless your runner supports in-source tests.
