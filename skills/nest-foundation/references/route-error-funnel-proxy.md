<!-- capsule-v2 -->
# RouterProxy — the outermost try/catch that turns handler throws into filter dispatches

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** Where is the boundary that converts an exception inside the whole route onion into an exception-filter call, and what does the error-layer twin do?

## createProxy / createExceptionLayerProxy
**Path/Symbol:** `packages/core/router/router-proxy.ts:createProxy` (:11-28), `createExceptionLayerProxy` (:30-53).
**Signature:** `createProxy(targetCallback: RouterProxyCallback, exceptionsHandler: ExceptionsHandler): (req, res, next) => Promise<void>`; `createExceptionLayerProxy(targetCallback: (err, req, res, next) => void, exceptionsHandler)`.
**Data Shape:** both return express-compatible async lambdas; on catch they build a fresh `ExecutionContextHost([req, res, next])` and delegate.

### Decisive source
```ts
return async (req, res, next) => {
  try {
    await targetCallback(req, res, next);
  } catch (e) {
    const host = new ExecutionContextHost([req, res, next]);
    exceptionsHandler.next(e, host);
    return res;                      // swallow: response handled by filters
  }
};
```

**Flow:** RouterExplorer wraps each composed route proxy with createProxy → any throw from guards/pipes/interceptors/handler/response-writing funnels to ExceptionsHandler.next → custom filters then BaseExceptionFilter. The adapter's OWN error middleware is registered via createExceptionLayerProxy, which rethrows a mapped exception INTO the same handler stack (`throw this.container.getHttpAdapterRef().mapException(err)` in RoutesResolver.registerExceptionHandler).
**Invariant:** After `exceptionsHandler.next` runs, the proxy RETURNS normally (resolves to res) instead of calling `next(e)` — the error must not re-enter Express's default handler or headers get written twice. The error-layer proxy exists because framework-level middleware errors arrive as (err,req,res,next) and must be TRANSLATED into Nest's filter world exactly once.
**Probe:** `packages/core/test/router/router-proxy.spec.ts` ("should method encapsulate async callback passed as argument" x2 layers); wiring pinned at `packages/core/router/routes-resolver.ts:169-188`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouterProxy createProxy createExceptionLayerProxy", limit: 5 });
```

## Verdict
Adopt one try/catch funnel per route plus a separate translation layer for framework errors; adapt host construction to your context shape; omit if your framework already funnels errors into filters natively. Porting wrong: calling next(e) after filter handling double-writes responses; translating framework errors at multiple layers re-runs filters on already-handled exceptions.
