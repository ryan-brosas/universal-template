<!-- capsule-v2 -->
# Request-scoped route proxy — REQUEST_CONTEXT_ID latch, durable-vs-mutating payload, error delegation to filters

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How does a request-scoped controller get its per-request container context, and what happens when context loading itself throws?

## getContextId / createRequestScopedHandler
**Path/Symbol:** `packages/core/router/router-explorer.ts:getContextId` (:489-511), `createRequestScopedHandler` (:437-487); `packages/core/injector/container.ts:registerRequestProvider` (:357-363).
**Signature:** `private getContextId<T>(request: T, isTreeDurable: boolean): ContextId`; `createRequestScopedHandler(wrapper, requestMethod, moduleRef, moduleKey, methodName): (req,res,next) => Promise<void>`.
**Data Shape:** `ContextId = { id: number, getParent?, payload? }`; REQUEST_CONTEXT_ID = `Symbol('REQUEST_CONTEXT_ID')` stamped on the request object.

### Decisive source
```ts
const contextId = ContextIdFactory.getByRequest(request);
if (!request[REQUEST_CONTEXT_ID as any]) {
  Object.defineProperty(request, REQUEST_CONTEXT_ID, {
    value: contextId, enumerable: false, writable: false, configurable: false,
  });                                            // one-shot latch per request
  const requestProviderValue = isTreeDurable
    ? contextId.payload                          // durable trees read payload only
    : Object.assign(request, contextId.payload); // mutating trees graft onto req
  this.container.registerRequestProvider(requestProviderValue, contextId);
}
return contextId;
```

**Flow:** static trees bind ONE proxy at registration; request-scoped routes get a proxy that per call: derive/reuse ContextId → latch it on the request → seed the REQUEST provider slot (`wrapper.setInstanceByContextId(contextId, { instance, isResolved: true })`) → `injector.loadPerContext` instantiates the controller subtree under that id → build callback proxy and dispatch. Any throw — INCLUDING loadPerContext failures — lands in the try/catch which creates an ExecutionContextHost and calls `exceptionFilter.next(err, host)`.
**Invariant:** The defineProperty latch makes the FIRST resolution authoritative; later enhancers calling getByRequest find the stamped symbol instead of generating a new id (otherwise guards/pipes/interceptors would see DIFFERENT request-scoped instances). Durable trees share instances via payload WITHOUT mutating the request; non-durable ones Object.assign payload onto the request. Context-loading errors are NOT 500s-by-crash — they flow through the same filter stack as handler errors.
**Probe:** `packages/core/test/router/router-explorer.spec.ts` ("should delegate error to exception filters" — asserts nextSpy receives Error + ExecutionContextHost); seeding pinned at `packages/core/injector/container.ts:357`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouterExplorer applyCallbackToRouter createRequestScopedHandler", limit: 5 });
```

## Verdict
Adopt the symbol-latch + single-registration-of-REQUEST pattern for any per-request DI scope; adapt the durable/mutating split to your instance-sharing rules; omit payload grafting if you never attach extras to requests. Porting wrong: regenerating context ids per enhancer forks the request scope into inconsistent instances; letting loadPerContext errors escape the filter stack turns DI failures into raw 500s.
