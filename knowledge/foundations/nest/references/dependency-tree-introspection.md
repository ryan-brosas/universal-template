<!-- capsule-v2 -->
# Dependency-tree introspection — how does the container know if a provider's WHOLE tree is request-scoped, and how is that cache invalidated?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How is "is this subtree static?" computed safely under circular graphs, and when must cached answers be dropped?

## InstanceWrapper.isDependencyTreeStatic / resetDependencyTreeState
**Path/Symbol:** `packages/core/injector/instance-wrapper.ts:isDependencyTreeStatic` (327-347), `isDependencyTreeDurable` (261-291), `introspectDepsAttribute` (293-325), `resetDependencyTreeState` (530-540).
**Signature:** `isDependencyTreeStatic(lookupRegistry: string[] = []): boolean`; `introspectDepsAttribute(callback, lookupRegistry)`.
**Data Shape:** memo fields `isTreeStatic`/`isTreeDurable` (undefined = not computed); module-level `WeakMap<InstanceWrapper, Set<InstanceWrapper>> dependencyTreeParents` maps child → its parents.

### Decisive source
```ts
public isDependencyTreeStatic(lookupRegistry = []): boolean {
  if (!isUndefined(this.isTreeStatic)) return this.isTreeStatic;   // memo
  if (this.scope === Scope.REQUEST) { this.isTreeStatic = false; ... return false; }
  this.isTreeStatic = !this.introspectDepsAttribute(
    (collection, registry) => collection.some(item => !item.isDependencyTreeStatic(registry)),
    lookupRegistry,
  );
  ...
}

// cycle-safe traversal: id-based registry, NOT a visited flag on nodes
if (lookupRegistry.includes(this[INSTANCE_ID_SYMBOL])) return false;
lookupRegistry = lookupRegistry.concat(this[INSTANCE_ID_SYMBOL]);

// any metadata write invalidates the WHOLE ancestor fan-in
private resetDependencyTreeState(lookupRegistry = new Set<string>()) {
  if (lookupRegistry.has(this[INSTANCE_ID_SYMBOL])) return;
  lookupRegistry.add(this[INSTANCE_ID_SYMBOL]);
  this.isTreeStatic = undefined; this.isTreeDurable = undefined;
  dependencyTreeParents.get(this)?.forEach(parent => parent.resetDependencyTreeState(lookupRegistry));
}
```

**Flow:** addCtor/Property/Enhancer metadata → register parent edge + reset self & ancestors → later queries recompute bottom-up and memoize.
**Invariant:** The registry is a path (concat per level), so diamonds don't abort evaluation but cycles terminate. Durable semantics differ: REQUEST scope defaults `durable:false`, and durability requires every non-static dep to be durable. Introspection covers ctor deps AND property deps AND enhancers.
**Probe:** `packages/core/test/injector/instance-wrapper.spec.ts::isDependencyTreeStatic` (circular reference cases at :33/:43, durable at :53).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "isDependencyTreeStatic introspectDepsAttribute resetDependencyTreeState", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt memoized subtree introspection with id-path registries and ancestor-fan-in invalidation; adapt the parent registry to your metadata model; omit durable propagation unless porting request scope. Porting wrong: recomputing without memoization explodes on wide graphs; caching without invalidation returns stale staticity after late enhancer registration.
