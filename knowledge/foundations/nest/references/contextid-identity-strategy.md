<!-- capsule-v2 -->
# ContextIdFactory — Math.random ids, symbol-latch reuse, and the strategy hook that re-parents durable subtrees

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Why are context ids just random numbers, how are they reused within one request, and what does a ContextIdStrategy attach?

## createContextId / getByRequest / apply
**Path/Symbol:** `packages/core/helpers/context-id-factory.ts:createContextId` (:5-15), `ContextIdFactory.getByRequest` (:57-84), `apply` (:91-93).
**Signature:** `createContextId(): ContextId` (`{ id: Math.random() }`); `static getByRequest<T>(request: T, propsToInspect: string[] = ['raw']): ContextId`.
**Data Shape:** `ContextId = { id, getParent?(info): ContextId, payload? }`; REQUEST_CONTEXT_ID symbol on the request (stamped by RouterExplorer) is the reuse latch.

### Decisive source
```ts
// id need NOT be unique/unpredictable: WeakMaps key on object REFERENCE,
// so equality comes from identity of the ContextId object, not its number.
return { id: Math.random() };

public static getByRequest(request, propsToInspect = ['raw']) {
  if (!request) return this.create();
  if (request[REQUEST_CONTEXT_ID as any]) return request[REQUEST_CONTEXT_ID];
  for (const key of propsToInspect) {
    if (request[key]?.[REQUEST_CONTEXT_ID]) return request[key][REQUEST_CONTEXT_ID];
  }
  if (!this.strategy) return this.create();
  const contextId = createContextId();
  const resolver = this.strategy.attach(contextId, request);
  if (this.isContextIdResolverWithPayload(resolver!)) {
    contextId.getParent = resolver.resolve;
    contextId.payload = resolver.payload;
  } else {
    contextId.getParent = resolver;          // bare function form
  }
  return contextId;
}
```

**Flow:** first caller per request creates the id AND latches it via defineProperty (RouterExplorer.getContextId) → every later enhancer lookup returns the SAME object → optional global strategy attaches getParent/payload so durable DI trees resolve against a PARENT context instead of the raw request one.
**Invariant:** Identity-not-value semantics underpin all wrapper caches — replacing `{id}` with an integer map breaks per-request isolation. The `'raw'` probe exists because adapters wrap the real request (`req.raw` in fastify); missing it forks contexts per transport. getParent receives `{token, isTreeDurable}` and answers where THIS dependency should resolve.
**Probe:** `packages/core/test/helpers/context-id-factory.spec.ts` ("should return an object with random \"id\" property"); latch behavior pinned at `packages/core/router/router-explorer.ts:494-500`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ContextIdFactory getByRequest createContextId", limit: 5 });
```

## Verdict
Adopt reference-identity context tokens + single creation point + optional re-parenting hook; adapt the latch mechanism to your request object; omit the strategy if you have no durable scopes. Porting wrong: value-equality ids silently merge unrelated requests, and skipping the raw-request probe double-instantiates request-scoped providers behind proxying adapters.
