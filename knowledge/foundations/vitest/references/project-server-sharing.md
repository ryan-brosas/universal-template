<!-- capsule-v2 -->
# Shared-server project topology — how do multiple test projects share ONE Vite server/runner without cross-project state bleed, and how do sibling resources get wired?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** When N projects must share a Vite dev server and module runner, what is owned per-project vs shared, and what identity key keeps their outputs apart?

## TestProject ownership + _spawnSibling
**Path/Symbol:** `packages/vitest/src/node/project.ts:TestProject` — hash (:91–93), `_initializeRunners` (:98–117), `createSpecification` (:162–177), `_spawnSibling` (:598–606), `_createBasicProject` (:574–586), `close()` single-flight (:440–457).
**Signature:** `static _spawnSibling(parent: TestProject, config: ResolvedConfig): TestProject`; `public createSpecification(moduleId: string, locationsOrOptions?, pool?, taskIdOverride?): TestSpecification`.
**Data Shape:** shared by reference: `vite: ViteDevServer`, `runner`, `_resolver`, `_fetcher`, `_serializedDefines`, `viteConfig`. Per-project: `config` (ResolvedConfig), `tmpDir = join(tmpdir(), nanoid())`, `hash = generateHash(config.root + config.name)`, `_provided` context, cached `testFilesList`.

### Decisive source
```ts
// identity is (root + name) — two projects sharing a server still get distinct hashes
this.hash = generateHash(this.config.root + this.config.name)
function generateHash(str: string): string {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = (hash << 5) - hash + char   // java-string-hash, 32-bit
    hash = hash & hash
  }
  return `${hash}`
}

// sibling shares EVERYTHING server-derived, owns ONLY its config slice
static _spawnSibling(parent: TestProject, config: ResolvedConfig): TestProject {
  const sibling = new TestProject(parent.vitest, parent.vite, parent.viteConfig, config)
  sibling.runner = parent.runner
  sibling._resolver = parent._resolver
  sibling._fetcher = parent._fetcher
  sibling._parent = parent
  sibling._serializedDefines = parent._serializedDefines
  return sibling
}

// close() is idempotent across restarts via cached promise
if (!this.closingPromise) {
  this.closingPromise = Promise.all([
    this.vite.close(), this.typechecker?.stop(), this.clearTmpDir(),
  ].filter(Boolean)).then(() => {
    if (!this.runner.isClosed()) return this.runner.close()
  }).then(() => { this._provided = {} as any })
}
return this.closingPromise
```

**Flow:** root project created from the global Vitest server (`_createBasicProject` reuses `vitest.runner/_resolver/_fetcher`) → additional projects either get their own server or are spawned as siblings of a primary (`sharedViteServer` flag records reuse; owner reports false) → specs are minted per project via `createSpecification` so each carries its project context → on close, one cached promise tears down vite + typechecker + tmpDir then runner.
**Invariant:** anything derived from the Vite server is shared BY REFERENCE and must never be re-created per sibling (double `ServerModuleRunner` on one environment breaks HMR); anything derived from `config` is per-project — especially `hash` (used to namespace worker/cache keys) and `tmpDir` (transformed-content isolation). `provide()` deliberately validates with `structuredClone` at write time because values cross process boundaries later. The closing promise MUST be cached: close can be invoked from both shutdown ordering and restart paths.
**Probe:** No dedicated unit test pins `_spawnSibling` directly (coverage caveat — graph callers live in core.ts server-creation paths); behavior is exercised end-to-end by multi-project e2e suites (`test/e2e/test/projects.test.ts`, `test/workspaces/vitest.config.watch.ts`). Cite the source range as ground truth when porting.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "_spawnSibling", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the share-server/own-config split and the (root+name) hash identity for any multi-tenant runner over one long-lived compiler/server. Adapt `structuredClone` validation to your serialization boundary; keep the cached-closing-promise idiom. Omit browser-cluster parenting (`_parentBrowser`) unless porting browser instances.
