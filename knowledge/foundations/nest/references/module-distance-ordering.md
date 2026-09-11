<!-- capsule-v2 -->
# Module distance ordering — how does the container turn the import graph into deterministic lifecycle ordering?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How are distances computed, why is it a tree walk over a cyclic graph, and when must it run?

## TopologyTree + calculateModulesDistance
**Path/Symbol:** `packages/core/scanner.ts:calculateModulesDistance` (414-433); `packages/core/injector/topology-tree/topology-tree.ts`; `packages/core/injector/topology-tree/tree-node.ts`.
**Signature:** `new TopologyTree(rootModule)`; `tree.walk((moduleRef, depth) => void)`.
**Data Shape:** depth = import-graph distance from root; globals pre-pinned at `Number.MAX_VALUE` in `NestContainer.setModule`.

### Decisive source
```ts
public calculateModulesDistance() {
  const modulesGenerator = this.container.getModules().values();
  modulesGenerator.next();                 // skip InternalCoreModule (index 0)
  const rootModule = modulesGenerator.next().value!;  // root module is index 1
  if (!rootModule) return;

  // Convert modules to an acyclic connected graph
  const tree = new TopologyTree(rootModule);
  tree.walk((moduleRef, depth) => {
    if (moduleRef.isGlobal) return;        // never overwrite the MAX pin
    moduleRef.distance = depth;
  });
}
```

**Flow:** after ALL modules are scanned but BEFORE global binding (`scan()` order comment: "after all modules are scanned but before global modules are registered") → walk from root assigning depths → later `getModulesToTriggerHooksOn` sorts descending by this value.
**Invariant:** The graph may contain cycles — TopologyTree converts it to an acyclic spanning tree via visited tracking; re-visiting a module through a shorter path updates its distance. Globals keep MAX so their hooks always fire first. Registration order (core=0, root=1) is load-bearing for root selection.
**Probe:** `packages/core/test/injector/topology-tree/topology-tree.spec.ts` + hook-order assertions in `packages/core/test/nest-application-context.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "TopologyTree calculateModulesDistance distance walk", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt depth-from-root as the single ordering key for lifecycle sequencing with globals pinned at MAX; adapt to BFS/DFS flavor as your graphs require; omit preview filtering. Porting wrong: computing distances after linking globals clobbers the MAX pin and reorders framework init ahead of user modules.
