<!-- capsule-v2 -->
# RouterExecutionContext.create — the HTTP handler assembly: guard→status→headers→SSE-signal→interceptors→pipes, built once per route

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What exact per-request order does an HTTP route proxy execute, which pieces are hoisted to creation time, and why does the SSE branch skip the await?

## create — the returned request proxy
**Path/Symbol:** `packages/core/router/router-execution-context.ts:create` (:88-193), `createPipesFn` (:396-431), `getMetadata` (:195-272).
**Signature:** `create(instance, callback, methodName, moduleKey, requestMethod, contextId?, inquirerId?): (req, res, next) => Promise<void>`.
**Data Shape:** metadata (argsLength, fnHandleResponse, isSseHandler, paramtypes, getParamsMetadata, httpStatusCode, responseHeaders) cached per controller+method in HandlerMetadataStorage; pipes/guards/interceptors instance arrays resolved at CREATE time.

### Decisive source
```ts
return async (req, res, next) => {
  const args = this.contextUtils.createNullArray(argsLength);
  fnCanActivate && (await fnCanActivate([req, res, next]));   // 1. guards FIRST
  this.responseController.setStatus(res, httpStatusCode);      // 2. status
  hasCustomHeaders && this.responseController.setHeaders(res, responseHeaders); // 3.
  if (isSseHandler) {
    this.attachSseAbortSignal(req);                            // 4. per-request AbortController
  }
  const resultOrDeferred = this.interceptorsConsumer.intercept( // 5. interceptor onion
    interceptors, [req, res, next], instance, callback,
    handler(args, req, res, next),                              //    6. pipes then callback inside
    contextType,
  );
  const result = isSseHandler ? resultOrDeferred : await resultOrDeferred; // 7.
  await (fnHandleResponse as HandlerResponseBasicFn)(result, res, req);    // 8.
};
```

**Flow:** creation time: reflect+cache handler metadata, resolve enhancer instances → per request: null-filled args array → guards (throw ForbiddenException on false) → setStatus/setHeaders → SSE abort latch → interceptors wrap a handler that awaits fnApplyPipes (`Promise.all(paramsOptions.map(resolveParamValue))`, global+param pipes via `pipes.concat(paramPipes)`) then `callback.apply(instance, args)` → response fn resolves Observables (unless SSE) and writes.
**Invariant:** Guards run BEFORE any status/headers are set (a rejected guard must not have already committed 200). Params resolve CONCURRENTLY but each into its fixed index slot. The SSE branch passes the UNAWAITED promise/Observable straight through — awaiting it first would break Promise&lt;Observable&gt; streaming (test pins the unresolved-promise passthrough). Status code defaults POST→201, everything else→200 unless @HttpCode overrides.
**Probe:** `packages/core/test/router/router-execution-context.spec.ts` ("should throw exception when \"tryActivate\" returns false", "should pass an unresolved Promise<Observable> to the SSE response handler", createPipesFn empty-params returns null).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouterExecutionContext create createPipesFn createHandleResponseFn", limit: 5 });
```

## Verdict
Adopt creation-time enhancer resolution + the eight-step per-request order; adapt the response-writing tail to your transport; omit the SSE branch only if you have no streaming handlers. Porting wrong: setting status before guards leaks headers on auth failures; awaiting the SSE result destroys deferred Observable streams.
