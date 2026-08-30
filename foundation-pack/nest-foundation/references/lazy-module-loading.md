<!-- capsule-v2 -->
# Lazy module loading — how can a module be loaded AFTER bootstrap and still see the fully wired container?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the re-entrant scan/instantiate protocol for post-boot modules, and when does load() short-circuit?

## LazyModuleLoader
**Path/Symbol:** `packages/core/injector/lazy-module-loader/lazy-module-loader.ts:LazyModuleLoader.load` (20-49).
**Signature:** `load(loaderFn: () => Type | DynamicModule | Promise<...>, loadOpts?: { logger?: boolean }): Promise<ModuleRef>`.
**Data Shape:** returns a real per-module `ModuleRef` instance (from the module's own provider map), not the abstract class.

### Decisive source
```ts
const moduleClassOrDynamicDefinition = await loaderFn();
const moduleInstances = await this.dependenciesScanner.scanForModules({ ..., lazy: true });
if (moduleInstances.length === 0) {
  // ALREADY loaded — just return the existing module's ModuleRef
  const { token } = await this.moduleCompiler.compile(moduleClassOrDynamicDefinition);
  const moduleInstance = this.modulesContainer.get(token)!;
  return this.getTargetModuleRef(moduleInstance);
}
const lazyModulesContainer = this.createLazyModulesContainer(moduleInstances); // dedup by Set, keyed by token
await this.dependenciesScanner.scanModulesForDependencies(lazyModulesContainer); // SAME scanner, scoped container
await this.instanceLoader.createInstancesOfDependencies(lazyModulesContainer);   // SAME two-pass loader
```
```ts
// scanner side — lazy re-entry skips ALREADY-INSTANTIATED duplicates
if (lazy && !moduleInserted && moduleInstance?.isInstantiated) return [];
...
if (lazy) this.container.bindGlobalsToImports(moduleInstance);
```

**Flow:** invoke loaderFn → scan with `lazy:true` (empty result ⇒ already present ⇒ compile token + return existing ModuleRef) → build a private Map for just the new modules → run the same dependency scan + two-pass instantiation on that subset → hand back target ModuleRef.
**Invariant:** The full scan+instantiate pipeline RE-RUNS but scoped to new modules only; globals must be re-bound into the lazy subtree explicitly. `isInstantiated` (instance present on the self provider) — not mere registration — decides skip.
**Probe:** `packages/core/test/injector/lazy-module-loader/lazy-module-loader.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "LazyModuleLoader load scanForModules lazy", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt re-running the standard pipeline over an isolated sub-container with already-instantiated short-circuit; adapt the ModuleRef handle to your resolution API; omit silent-logger swapping. Porting wrong: naively calling createInstancesOfDependencies on the WHOLE container after boot re-triggers lifecycle hooks.
