<!-- capsule-v2 -->
# Request-scope registration + durable context parenting — how does a per-request payload become injectable, and how do durable trees pick their parent context?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How is the REQUEST token pre-wired, and when does a child's contextId get re-parented?

## registerRequestProvider + getContextId
**Path/Symbol:** `packages/core/injector/container.ts:registerRequestProvider` (357-363); `packages/core/injector/injector.ts:getContextId` (1287-1297); `packages/core/router/request/request-providers.ts:requestProvider`; `instance-wrapper.ts:ContextId` (42-46).
**Signature:** `registerRequestProvider<T>(request: T, contextId: ContextId): void`; `contextId.getParent?(info: {token, isTreeDurable}): ContextId`.
**Data Shape:** REQUEST wrapper lives on InternalCoreModule with `isResolved:true`; each context stores `{instance, isResolved:true}` under its ContextId.

### Decisive source
```ts
public registerRequestProvider<T = any>(request: T, contextId: ContextId) {
  const wrapper = this.internalCoreModule.getProviderByKey(REQUEST);
  wrapper.setInstanceByContextId(contextId, { instance: request, isResolved: true });
}

// injector — durable subtrees may resolve under a DIFFERENT (shared) context
private getContextId(contextId: ContextId, instanceWrapper: InstanceWrapper): ContextId {
  return contextId.getParent
    ? contextId.getParent({
        token: instanceWrapper.token,
        isTreeDurable: instanceWrapper.isDependencyTreeDurable(),
      })
    : contextId;
}
```

**Flow:** transport layer creates a ContextId per request → registerRequestProvider seeds REQUEST before any handler resolves → every lookup in that request re-keys through getContextId; non-durable request-scoped deps use the raw per-request id, durable ones consult getParent to share an aggregate context.
**Invariant:** The REQUEST provider must be seeded BEFORE resolution (handlers assume presence); it is always `isResolved` so it never triggers loading. Durable re-parenting is opt-in per wrapper via tree introspection — default trees stay per-request.
**Probe:** `packages/core/test/nest-application-context.spec.ts::registerRequestByContextId` paths + router request-context specs (`packages/core/test/router/`).
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "registerRequestProvider REQUEST contextId getParent", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pre-seeded per-context REQUEST slot on the internal module plus optional durable re-parenting hook; adapt seeding point to your transport; omit durability if you don't need cross-request aggregation. Porting wrong: resolving REQUEST lazily during handler execution races the first injection and yields undefined payloads.
