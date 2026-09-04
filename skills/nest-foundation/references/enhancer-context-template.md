<!-- capsule-v2 -->
# ContextCreator base — the global→class→method concat template shared by every enhancer family

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How do guards/pipes/interceptors/filters all resolve their instance lists, and where do scoped (contextId) globals differ from static ones?

## ContextCreator.createContext
**Path/Symbol:** `packages/core/helpers/context-creator.ts:createContext` (:16-41), `reflectClassMetadata` (:43-46), `reflectMethodMetadata` (:48-53), `getContextId` (:55-65).
**Signature:** `createContext<T, R>(instance, callback, metadataKey: string, contextId = STATIC_CONTEXT, inquirerId?): R`; abstract `createConcreteContext(metadata, contextId?, inquirerId?): R`; optional `getGlobalMetadata?(contextId?, inquirerId?): T`.
**Data Shape:** three metadata arrays (global instances/wrappers, class-level, method-level) each mapped through the subclass's concrete-context factory.

### Decisive source
```ts
return [
  ...this.createConcreteContext(globalMetadata || [], contextId, inquirerId),
  ...this.createConcreteContext(classMetadata, contextId, inquirerId),
  ...this.createConcreteContext(methodMetadata, contextId, inquirerId),
] as R;

protected getContextId(contextId: ContextId, instanceWrapper: InstanceWrapper): ContextId {
  return contextId.getParent
    ? contextId.getParent({ token: instanceWrapper.token,
                            isTreeDurable: instanceWrapper.isDependencyTreeDurable() })
    : contextId;
}
```

**Flow:** subclass `.create()` sets moduleContext then delegates here → globals resolved first (order matters: they run FIRST in the chain) → class metadata read from prototype's CONSTRUCTOR, method metadata from the callback itself → each entry flows through the subclass filter ladder (`name || intercept/canActivate/transform/catch` duck-typing → container lookup → instance-host fetch).
**Invariant:** The concat ORDER (global, class, method) is fixed and consumers depend on it — guards run globals first; filters get reversed afterwards. Static contexts return pre-built arrays untouched; REQUEST-scoped globals re-resolve per request via `getInstanceByContextId(getContextId(...))`, and durable-tree members ask their wrapper for a re-parented id. Instance lookup is scoped to `moduleRef.injectables.get(metatype)` of the ROUTE'S module only — cross-module providers silently yield null and are DROPPED, not errors.
**Probe:** `packages/core/test/pipes/pipes-context-creator.spec.ts` + `interceptors-context-creator.spec.ts` (same-shape ladders); scoped-global branch pinned by `getGlobalRequestPipes/Guards/Interceptors` consumers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ContextCreator createContext reflectClassMetadata getContextId", limit: 5 });
```

## Verdict
Adopt one template-method base for ALL enhancer families so ordering semantics stay uniform; adapt the duck-typing predicates to your decorator set; omit getParent re-parenting if you have no durable trees. Porting wrong: flipping concat order changes execution semantics of every enhancer at once, and dropping the null-instance filter turns unregistered globals into runtime TypeErrors mid-request.
