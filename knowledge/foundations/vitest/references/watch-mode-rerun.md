<!-- capsule-v2 -->
# Watch-mode two-set invalidation — how does a changed non-test file decide WHICH tests to rerun without missing indirect importers or rerunning everything?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** When chokidar fires for an arbitrary source file, how does the watcher separate "tests that must re-run" from "modules that must be invalidated" so the next run picks exactly the affected specs?

## VitestWatcher.changedTests / invalidates sets
**Path/Symbol:** `packages/vitest/src/node/watcher.ts:VitestWatcher` — `changedTests`/`invalidates` (:12–16), `onFileChange` (:84–98), `handleSetupFile` (:147–166), `handleFileChanged` recursion (:171–239).
**Signature:** `public onFileChange = (id: string): void`; `private handleFileChanged(filepath: string): boolean`.
**Data Shape:** `invalidates: Set<string>` = module paths handed to `pool.runTests(specs, invalidates)` as Vite-invalidation seeds; `changedTests: Set<string>` = test file paths drained by the debounced rerun. The boolean return of `handleFileChanged` is literally "changedTests was mutated".

### Decisive source
```ts
// handleFileChanged — module-graph importer walk with self-recursion guard
if (this.changedTests.has(filepath) || this.invalidates.has(filepath)) {
  return false                      // already accounted for: do not recurse again
}
if (pm.isMatch(filepath, this.vitest.config.forceRerunTriggers)) {
  this.vitest.state.getFilepaths().forEach(file => this.changedTests.add(file))
  return true                       // force trigger => every known test reruns
}
if (this.handleSetupFile(filepath)) return true   // setup file => all its project's files

const projects = this.vitest.projects.filter((project) => {
  return project._getViteEnvironments().some(({ moduleGraph }) => {
    return moduleGraph.getModulesByFile(filepath)?.size
  })
})
if (!projects.length) {
  // server was restarted: importer info is gone, fall back to "is it a test at all"
  if (this.vitest.state.filesMap.has(filepath) || this.vitest.projects.some(project => project._isCachedTestFile(filepath))) {
    this.changedTests.add(filepath)
    return true
  }
  return false
}
// per project: if the changed file IS a run/cached test → add it;
// otherwise walk mod.importers recursively through handleFileChanged
let rerun = false
for (const mods of environmentMods) {
  for (const mod of mods || []) {
    mod.importers.forEach((i) => {
      const needsRerun = this.handleFileChanged(i.file)   // RECURSION
      if (needsRerun) rerun = true
    })
  }
}
```

**Flow:** change event → `slash(id)` + `invalidateFile(id)` (all projects' Vite module graphs) → custom `watchTriggerPatterns` shortcut → `handleFileChanged`: guard-set check → forceRerunTriggers global add → setup-file fan-out → per-project module-graph lookup → recursive importer climb adding each reachable test to `changedTests`. Later, `Vitest.scheduleRerun`'s debounce drains `changedTests` into specs while `runFiles` snapshots+clears `invalidates` and passes them to the pool (`core.ts:1007–1019`).
**Invariant:** the two sets answer different questions and must never be merged — a file can sit in BOTH (`invalidates` at watcher.ts:208, then added to `changedTests` at :212 if it is itself a test). The recursion guard ("already in either set ⇒ return false") is what makes the importer walk finite on diamond dependency graphs; dropping it causes exponential re-walks. After a server restart importer edges are gone BY DESIGN — the fallback treats only known/cached test files as affected.
**Probe:** `test/e2e/test/watch/file-watching.test.ts` — editing `math.ts` reruns only its importer (`'RERUN  ../math.ts'`, `'1 passed'`, :55–63); forceRerunTriggers edit reruns ALL suites (`'2 passed'`, :87–109); deleting a test reports `Test removed` (rename test :183–224 pairs unlink→`onTestRemoved`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "handleFileChanged", limit: 5, fields: ["signature", "name", "file"] });
```
Trace: `trace_path --function-name handleFileChanged` → callee `handleSetupFile`, callers `onFileChange`/`onFileCreate`.

## Verdict
Adopt the two-set split + guarded importer recursion (works for any HMR-style module graph host). Adapt the graph source (Vite `moduleGraph.getModulesByFile`) and the setup-file/config ownership model to your host's dependency tracker. Omit `watchTriggerPatterns` unless you need user-defined watch triggers.
