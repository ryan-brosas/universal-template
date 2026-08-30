<!-- capsule-v2 -->
# Listener registration pipeline — how do decorated controller methods become transport handlers across many servers?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you scan @MessagePattern/@EventPattern metadata once and register handlers on every compatible transport server, handling static vs request-scoped instances and RPC error funnels?

## Metadata scan → transport filter → proxy or request-scoped closure
**Path/Symbol:** `packages/microservices/listener-metadata-explorer.ts:ListenerMetadataExplorer.explore/exploreMethodMetadata` (41-84); `packages/microservices/listeners-controller.ts:ListenersController.registerPatternHandlers` (66-164), `createRequestScopedHandler` (229-305).
**Signature:** `explore(instance): EventOrMessageListenerDefinition[]`; `registerPatternHandlers(wrapper: InstanceWrapper<Controller>, serverInstance: Server, moduleKey: string)`.
**Data Shape:** definition = `{patterns[], methodKey, isEventHandler, targetCallback, transport?, extras?}`; metadata keys `PATTERN_HANDLER_METADATA` (gate), `PATTERN_METADATA`, `TRANSPORT_METADATA`, `PATTERN_EXTRAS_METADATA`.

### Decisive source
```ts
// scan gates on handler-type metadata; callback read from INSTANCE not prototype
const handlerType = Reflect.getMetadata(PATTERN_HANDLER_METADATA, prototypeCallback);
if (isUndefined(handlerType)) return;
const targetCallback = instance[methodKey];
...
isEventHandler: handlerType === PatternHandler.EVENT,
// registration sweep: one controller serves many servers via the transport filter
.filter(({ transport }) =>
  isUndefined(transport) || isUndefined(serverInstance.transportId) ||
  transport === serverInstance.transportId)
.flatMap(handler => handler.patterns.map(pattern => ({ ...handler, patterns: [pattern] })))
// static tree: ONE proxy per registration
if (isStatic) {
  const proxy = this.contextCreator.create(instance, targetCallback, moduleKey, methodKey,
    STATIC_CONTEXT, undefined, defaultCallMetadata);
  // event handlers get an extra wrapper that strips RequestContextHost and forkJoins the .next chain
}
// request-scoped: synthesize-or-strip sentinel host, load instance per context, rebuild proxy per message
let [dataOrContextHost] = args;
if (dataOrContextHost instanceof RequestContextHost) { contextId = this.getContextId(...); args.shift(); }
else { const [data, reqCtx] = args; const request = RequestContextHost.create(pattern, data, reqCtx); /* ... */ }
const contextInstance = await this.injector.loadPerContext(instance, moduleRef, collection, contextId);
// error funnel: WeakMap-cached filter per handler method, ExecutionContextHost typed 'rpc'
catch (err) {
  let exceptionFilter = this.exceptionFiltersCache.get(instance[methodKey]); // create+cache on miss
  const host = new ExecutionContextHost(args); host.setType('rpc');
  return exceptionFilter.handle(err, host);
}
```

**Flow:** explore scans prototype methods → definitions flatMapped to single patterns → transport-filtered per server → static trees bind one proxy; non-static trees wrap a request-scoped async handler that materializes a `RequestContextHost` sentinel (stripped for events, synthesized from `[data, ctx]` for messages), loads the scoped instance, builds the proxy per message, and catches everything into an rpc-typed exception filter. Event wrappers additionally compose chained handlers via forkJoin.
**Invariant:** one sweep per controller per server; decorator-level transport pins scope handlers to matching servers while unpinned handlers land everywhere; sync errors in request-scoped handlers NEVER escape as broker faults — they funnel through the cached filter.
**Probe:** `packages/microservices/test/listeners-controller.spec.ts` (describe blocks: registerPatternHandlers / when request scoped / createRequestScopedHandler 'when "loadPerContext" throws'); `packages/microservices/test/listeners-metadata-explorer.spec.ts` (@MessagePattern/@EventPattern multi-pattern metadata, missing handler-type metadata ⇒ undefined, scanForClientHooks skips function-valued members).
**Runner caveat:** direct test execution blocked (deps uninstalled); describe-level behavior verified by direct spec read.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "registerPatternHandlers request scoped handler exception filter", file_pattern: "packages/microservices/listeners-controller.ts", limit: 8 });
// live @ pin: rank#1 createRequestScopedHandler 229-305, rank#2 registerPatternHandlers 66-164
await mcp.codebase_memory.search_graph({ project: "nest", query: "exploreMethodMetadata pattern handler metadata event", file_pattern: "packages/microservices/listener-metadata-explorer.ts", limit: 8 });
// live @ pin: rank#1 exploreMethodMetadata 52-84
```

## Verdict
Adopt the metadata-gated scan, transport filter, static/request-scoped split, sentinel-host arg convention, and WeakMap-cached rpc exception funnel; adapt `Reflect.getMetadata` keys and `MetadataScanner` to your decoration layer; omit GraphInspector entrypoint recording unless porting inspection.
