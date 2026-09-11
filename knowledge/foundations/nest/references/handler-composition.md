<!-- capsule-v2 -->
# Handler context composition — how does a routed method become a guarded, pipe-transformed, interceptor-wrapped, filter-protected callable?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the exact composition order of the handler onion, and why are params metadata produced lazily?

## ExternalContextCreator.create
**Path/Symbol:** `packages/core/helpers/external-context-creator.ts:create` (94-188), `createPipesFn` (302-330), `getMetadata` (190-242).
**Signature:** `create(instance, callback, methodName, metadataKey?, paramsFactory?, contextId?, inquirerId?, options?, contextType?): Function`.
**Data Shape:** `ExternalHandlerMetadata = { argsLength, paramtypes, getParamsMetadata(moduleKey, contextId?, inquirerId?) }`, cached per instance+method in `HandlerMetadataStorage`.

### Decisive source
```ts
const target = async (...args) => {
  const initialArgs = this.contextUtils.createNullArray(argsLength);  // positional slots
  fnCanActivate && (await fnCanActivate(args));        // 1. guards (throw Forbidden)
  const result = await this.interceptorsConsumer.intercept(  // 2. interceptors around handler
    interceptors, args, instance, callback,
    handler(initialArgs, ...args),                     //    3. pipes fill args, then callback
    contextType,
  );
  return this.transformToResult(result);               // 4. Observable → last value
};
return options.filters
  ? this.externalErrorProxy.createProxy(target, exceptionFilter, contextType)  // 5. outermost filter
  : target;
```

**Flow:** resolve module key by scanning which module has the instance as provider → cached metadata lookup → pre-resolve pipes/guards/filters/interceptors instances at CREATION time (request-scoped ones resolved via contextId) → compose onion: filters ∘ interceptors ∘ guards ∘ pipes∘handler.
**Invariant:** Guards see the RAW transport args; pipes only run for declared params (`paramsOptions.length ? pipesFn : null`); argument array is null-padded to `argsLength` so param indexes stay stable; enhancer instantiation happens when the handler is created, not per call.
**Probe:** `packages/core/test/helpers/external-context-creator.spec.ts` + router-level composition in `packages/core/router/` specs.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "ExternalContextCreator create createPipesFn intercept", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the five-layer onion (filters outside, pipes innermost) built once per route with pre-resolved enhancers; adapt layer set to your framework; omit RxJS interop if you have no Observables. Porting wrong: running guards after interceptors changes retry/auth semantics and breaks filter coverage of guard failures.
