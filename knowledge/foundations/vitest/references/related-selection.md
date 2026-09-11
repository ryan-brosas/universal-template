<!-- capsule-v2 -->
# Related-test selection — how does `--changed`/`--related` map changed source files to the test files that transitively import them?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How do you compute the affected-test set from a Vite module graph without expanding any module more than once, and when must the answer be "run nothing" vs "run everything"?

## VitestSpecifications.filterTestsBySource
**Path/Symbol:** `packages/vitest/src/node/specifications.ts:VitestSpecifications.filterTestsBySource` (123–168) + `getAffectedModules` (176–262); entry `getRelevantTestSpecifications` (36–40).
**Signature:** `private async filterTestsBySource(specs: TestSpecification[]): Promise<TestSpecification[]>`; `getAffectedModules(project, specs, related): Promise<Set<string>>`.
**Data Shape:** `related: string[]` (changed files; populated once per session from the VCS provider and cached on `config.related`); builds a reverse-import edge map `importers: Map<fsPath, Set<importer>>`, a shared `visited` set, an `existsCache`, and a hand-rolled concurrency limiter over `environment.transformRequest`.

### Decisive source
```ts
const forceRerunTriggers = this.vitest.config.forceRerunTriggers
const matcher = forceRerunTriggers.length ? pm(forceRerunTriggers) : undefined
if (matcher && related.some(file => matcher(file))) {
  return specs                                  // e.g. a config file changed -> run ALL tests
}
// don't run anything if no related sources are found (watch mode still processes all tests)
if (!this.vitest.config.watch && !related.length) {
  return []
}
...
const addImports = async (filepath) => {
  // `visited` is shared by every spec in the project, so a module is
  // expanded once per run instead of once per test file that reaches it.
  if (visited.has(filepath)) return
  visited.add(filepath)
  const transformed = mod?.transformResult || await withLimit(() => environment.transformRequest(filepath))
  const dependencies = [...transformed.deps || [], ...transformed.dynamicDeps || []]
  ...record importer edges; skip node_modules / non-existent paths via existsCache...
}
await Promise.all(specs.map(spec => addImports(spec.moduleId)))

const affected = new Set<string>(related)
const queue = [...related]
while (queue.length) {                          // reverse BFS over importer edges
  const importedBy = importers.get(queue.pop()!)
  for (const importer of importedBy ?? []) {
    if (!affected.has(importer)) { affected.add(importer); queue.push(importer) }
  }
}
return specs.filter(spec => affected.get?.call(affected, spec.moduleId))
```

**Flow:** glob all specs → if `changed` without explicit `related`, ask the VCS provider once for changed files → short-circuits: forceRerunTriggers match ⇒ all tests; empty related outside watch ⇒ none → per project: expand every spec's import closure ONCE into reverse edges (concurrency-capped transforms, existence cache, node_modules pruned) → reverse-BFS from related files → keep only specs in the affected set.

**Invariant:** (1) each module's imports are expanded at most once per run across ALL specs of a project (the doc comment names this exact optimization); (2) dynamic imports count as edges (`dynamicDeps`); (3) force-rerun triggers override graph logic entirely; (4) in watch mode an empty related set means "keep watching", not "exit".

**Probe:** `test/e2e/test/watch/related.test.ts` (:9 'when nothing is changed, run nothing but keep watching'); `git-changed.test.ts` and `list-changed.test.ts` pin VCS integration.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "filterTestsBySource getAffectedModules forceRerunTriggers related", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.node.specifications.VitestSpecifications.getAffectedModules
```

## Verdict
Adopt the expand-once reverse-edge map + reverse-BFS affected-set computation with the three short-circuit rules. Adapt the edge source (any transform/import extractor) and the VCS provider boundary. Omit Windows `/@fs/` path slicing details unless the host is path-style-sensitive.
