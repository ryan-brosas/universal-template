<!-- capsule-v2 -->
# RPC context-creator args ladder — how does the enhancer machinery assemble handler arguments from a positional broker packet?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** HTTP handlers get arguments from a request object; RPC handlers get them from a flat `(data, ctx, call?)` tuple — how do decorated parameter types map onto that tuple, and where do guards/pipes/interceptors/pre-request hooks slot in?

## Position table + null-array sizing over the shared enhancer consumers
**Path/Symbol:** `packages/microservices/context/rpc-context-creator.ts:RpcContextCreator.create` (62-169), `exchangeKeysForValues` (245-283), `createPipesFn` (285-311), `createGuardsFn` (179-198); `packages/microservices/factories/rpc-params-factory.ts:RpcParamsFactory.exchangeKeyForValue` (4-22).
**Signature:** `create(instance, callback, moduleKey, methodName, contextId = STATIC_CONTEXT, inquirerId?, defaultCallMetadata?): (...args) => Promise<Observable<any>>`; `exchangeKeyForValue(type: number, data: string | undefined, args: unknown[]): unknown`.
**Data Shape:** handler metadata cached per (instance, methodName) in HandlerMetadataStorage as `{argsLength, paramtypes, getParamsMetadata(moduleKey)}`; initialArgs = `contextUtils.createNullArray(argsLength)` (max-index+1 sizing, same as context-utils-args-assembly capsule).

### Decisive source
```ts
// THE position table — everything else is plumbing around it:
public exchangeKeyForValue(type: number, data: string | undefined, args: unknown[]) {
  if (!args) return null;
  switch (type as RpcParamtype) {
    case RpcParamtype.PAYLOAD:   return data ? args[0]?.[data] : args[0];
    case RpcParamtype.CONTEXT:   return args[1];
    case RpcParamtype.GRPC_CALL: return args[2];
    default:                     return null;
  }
}

// create() — pipes fill a pre-sized null array in parallel, then the handler runs on it:
const initialArgs = this.contextUtils.createNullArray(argsLength);
// ...
const handler = (initialArgs, args) => async () => {
  if (fnApplyPipes) {
    await fnApplyPipes(initialArgs, ...args);   // Promise.all over paramsOptions
    return callback.apply(instance, initialArgs);
  }
  return callback.apply(instance, args);        // no pipes ⇒ raw tuple passthrough
};
// guards: tryActivate false ⇒ throw new RpcException(FORBIDDEN_MESSAGE)
// pre-request hooks: recursive next() chain over defer(() => from(executePipeline()).pipe(mergeMap(o => o)))
```

**Flow:** create() builds exception-filter/pipes/guards/interceptor contexts all with contextType 'rpc' ⇒ returns rpcProxy.create(pipeline, exceptionHandler). Per message: global pre-request hooks run FIRST (registration order, fast-path skip when none) with an ExecutionContextHost typed 'rpc' exposing getClass()/getHandler() ⇒ guards tryActivate (false ⇒ RpcException(FORBIDDEN_MESSAGE)) ⇒ interceptors wrap the handler ⇒ pipes resolve each decorated param via extractValue(...args) in PARALLEL into initialArgs[index] (global pipes concat per-param pipes; schema-aware via ArgumentMetadata {metatype, type, data, schema}) ⇒ callback.apply. Custom route args (key includes CUSTOM_ROUTE_ARGS_METADATA) bypass the position table and use their factory.
**Invariant:** PAYLOAD is the ONLY param type that can extract a property (`@Payload('data')` ⇒ args[0].data); CONTEXT/GRPC_CALL are pure positions (args[1]/args[2]) — adding a new param type means extending exactly one switch; when no pipes exist the raw args tuple is passed through UNTOUCHED (no array copy), so handlers without decorators pay zero assembly cost; guard denial is an RpcException (not a thrown string) so the RPC exception funnel serializes it like any other handler error.
**Probe:** `packages/microservices/test/context/rpc-context-creator.spec.ts` (pins tryActivate call, forbidden-RpcException on false, exchangeKeysForValues mapping for PAYLOAD/CONTEXT/custom-route keys, createPipesFn null-vs-function, pre-request hooks order + fast-path + ExecutionContext getClass/getHandler) and `test/factories/rpc-params-factory.spec.ts` (pins payload-without-data ⇒ args[0], payload-with-data ⇒ args[0][data], context ⇒ args[1], missing args ⇒ null).
**Runner caveat:** repo deps uninstalled (vitest blocked); expectations quoted from spec sources read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", file_pattern: "rpc-context-creator.ts", fields: ["lines"], limit: 40 });
// expected @ pin: create 62-169, createGuardsFn 179-198, exchangeKeysForValues 245-283, createPipesFn 285-311
await mcp.codebase_memory.search_graph({ project: "nest", qn_pattern: ".*microservices.factories.rpc-params-factory.RpcParamsFactory", limit: 10 });
```

## Verdict
Adopt "one tiny position-table factory + cached per-method metadata" as the seam between declarative parameter decorators and imperative handler invocation — it keeps the enhancer consumers (guards/pipes/interceptors) transport-agnostic while each transport supplies its own tuple shape. Adopt the raw-passthrough fast path when no pipes exist. Adapt the tuple layout to your broker's delivery shape (NATS gives (data, ctx), gRPC adds the call object at index 2); omit GRPC_CALL entirely for non-gRPC transports. Keep guard-denial as a typed exception so the same filter chain handles it — never a control-flow return.
