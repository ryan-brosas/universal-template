<!-- capsule-v2 -->
# Test-run state manager — how does the node process keep per-file/per-task state consistent when the same file runs under multiple projects, and how are unhandled errors and cancels recorded?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** What is the identity rule for file tasks across projects/runs, and how do unhandled errors flow into the exit code?

## StateManager maps
**Path/Symbol:** `packages/vitest/src/node/state.ts:StateManager` (18–278) — `catchError` (62–89), `collectFiles` (150–168), `clearFiles` (170–199), `updateTasks` (233–245), `cancelFiles` (263–277), `isAggregateError` (10–16).
**Signature:** `filesMap: Map<string, File[]>`; `idMap: Map<string, Task>`; `taskFileMap: WeakMap<Task, File>`; `errorsSet: Set<unknown>`; `catchError(error: unknown, type: string): void`.
**Data Shape:** filesMap is keyed by FILEPATH with an ARRAY of File tasks — one per (projectName, meta.typecheck, meta.__vitest_label__) tuple; task ids are content-hash ids (`generateFileHash(relativePath, project.name)`) so the same path yields different ids per project.

### Decisive source
```ts
collectFiles(project, files = []) {
  files.forEach((file) => {
    const existing = this.filesMap.get(file.filepath) || []
    const currentFile = existing.find(
      i => i.projectName === file.projectName
        && i.meta.typecheck === file.meta.typecheck
        && i.meta.__vitest_label__ === file.meta.__vitest_label__,
    )
    // keep logs from the previous incarnation of this file
    if (currentFile) { file.logs = currentFile.logs }
    const otherFiles = existing.filter(i => i !== currentFile)
    otherFiles.push(file)
    this.filesMap.set(file.filepath, otherFiles)
    this.updateId(file, project)
  })
}

cancelFiles(files, project) {
  // if we don't filter existing modules, they will be overridden by `collectFiles`
  const nonRegisteredFiles = files.filter(({ filepath }) => {
    const relativePath = relative(project.config.root, filepath)
    const id = generateFileHash(relativePath, project.name)
    return !this.idMap.has(id)
  })
  this.collectFiles(project, nonRegisteredFiles.map(file =>
    createFileTask(file.filepath, project.config.root, project.config.name)))
}
```

**Flow:** specs register paths → workers push result packs (`updateTasks`: sets `task.result`/`task.meta`, flips mode to skip on `state === 'skip'`) → errors arrive via `catchError`, which flattens AggregateErrors recursively, stamps `.type`, special-cases `VITEST_PENDING` (marks the task skipped instead of recording an error), and consults the optional `onUnhandledError` filter before adding to `errorsSet` → at run end `getUnhandledErrors()` feeds `_testRun.end` and `_checkUnhandledErrors` sets `process.exitCode = 1`.

**Invariant:** (1) same file + different project/typecheck/label = SEPARATE File entries under one filepath key; re-collect replaces only the matching incarnation while preserving its logs; (2) cancelFiles must not create placeholder tasks for files already registered by a worker (the idMap pre-filter comment names that exact override bug class); (3) unhandled errors always end up in the exit code unless `dangerouslyIgnoreUnhandledErrors`.

**Probe:** e2e suite pins multi-project state via `test/e2e/test/projects.test.ts` and reported entities via `reported-tasks.test.ts`; unhandled-rejection accounting pinned by `test/e2e/test/unhandled-rejections.test.ts`. Coverage caveat: probes read on disk at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "StateManager catchError collectFiles clearFiles cancelFiles VITEST_PENDING", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.node.state.StateManager
```

## Verdict
Adopt the keyed-array state layout with the three-field file-identity rule, log preservation across recollect, the idMap-guarded cancel placeholder creation, and AggregateError-flattening error capture. Adapt the hash function and metadata fields to the host. Omit blob-merge fields (`blobs`) and benchmark/startup metrics unless porting merge-reports.
