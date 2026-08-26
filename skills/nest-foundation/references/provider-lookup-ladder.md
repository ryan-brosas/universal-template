<!-- capsule-v2 -->
# Provider lookup ladder — in what order is a token searched across module boundaries, and why stop at the first export match?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What visibility rules decide whether a dependency resolves, and what does the traversal memoize?

## Injector.lookupComponent family
**Path/Symbol:** `packages/core/injector/injector.ts:lookupComponent` (605-636) → `lookupComponentInParentModules` (638-662) → `lookupComponentInImports` (664-720).
**Signature:** `lookupComponentInImports(moduleRef, name, wrapper, moduleRegistry: Set<string> = new Set(), resolutionContext?, keyOrIndex?, isTraversing?: boolean): Promise<InstanceWrapper | null>`.
**Data Shape:** `moduleRegistry` of visited Module ids (cycle guard); `isTraversing` flips on after the first hop.

### Decisive source
```ts
// 1. self-reference with the same token = unknown dependency (fail fast)
if (wrapper && token === name) throw new UnknownDependenciesException(...);
// 2. host module's own providers
if (name && providers.has(name)) { ...addDependencyMetadata(...); return instanceWrapper; }
// 3. imports graph — DFS
let children = [...imports.values()];
if (isTraversing) {
  children = children.filter(child => contextModuleExports.has(child.metatype));
}
for (const relatedModule of children) {
  if (moduleRegistry.has(relatedModule.id)) continue;   // visited set, not recursion cap
  ...
  if (!exports.has(name) || !providers.has(name)) {
    // re-export passthrough: keep searching THROUGH non-exporting modules
    const instanceRef = await this.lookupComponentInImports(relatedModule, ...isTraversing=true);
    ...
  }
  instanceWrapperRef = providers.get(name)!;
  /**
   * Stop at the first direct export match. Continuing when the provider is
   * already resolved would let a later import (e.g. a global forRoot module)
   * override an explicit forFeature import for the same token.
   */
  break;
}
```

**Flow:** own providers → direct imports → deeper imports (only via exported providers once past the first hop) → null ⇒ `UnknownDependenciesException`.
**Invariant:** Visibility = exported ∧ provided at every hop beyond the immediate import. First match wins — do NOT keep searching after a resolved hit or global `forRoot` providers would shadow explicit `forFeature` configuration.
**Probe:** `packages/core/test/injector/injector.spec.ts:539` ("should stop at the first direct export match when it is already resolved") and `:563`, plus the UnknownDependenciesException cases at `:417`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "lookupComponentInImports exports providers moduleRegistry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-step ladder with visited-set memoization and first-match-wins semantics; adapt error message enrichment to your DI surface; omit enhancer subtype plumbing. Porting wrong: continuing the search past the first found export silently changes which configured instance gets injected.
