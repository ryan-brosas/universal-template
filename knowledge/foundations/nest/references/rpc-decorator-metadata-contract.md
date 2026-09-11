<!-- capsule-v2 -->
# RPC decorator metadata contract — what metadata do decorated handlers expose to the listener pipeline?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** When handlers are declared with decorators instead of config, which metadata keys form the contract the wiring pipeline scans — and how do overloaded decorator arguments (pattern vs transport vs extras) stay unambiguous?

## Four-key method metadata + argument-disambiguation ladder
**Path/Symbol:** `packages/microservices/decorators/message-pattern.decorator.ts:MessagePattern` (37-93), `createGrpcMethodMetadata` (210-229), `GrpcStreamMethod` (126-179); `decorators/event-pattern.decorator.ts:EventPattern` (37-88); `decorators/client.decorator.ts:Client` (15-25); `decorators/payload.decorator.ts:Payload` (87-103); `utils/param.utils.ts:createPipesRpcParamDecorator`.
**Signature:** `MessagePattern(metadata?, transportOrExtras?, maybeExtras?): MethodDecorator`; `Client(metadata?: ClientOptions): PropertyDecorator`; `Payload(propertyOrPipe?, optionsOrPipe?, ...pipes): ParameterDecorator`.
**Data Shape:** method-level keys on `descriptor.value`: PATTERN_METADATA (ARRAY — multiple patterns per method), PATTERN_HANDLER_METADATA (PatternHandler.MESSAGE|EVENT — the gate ListenerMetadataExplorer scans), TRANSPORT_METADATA, PATTERN_EXTRAS_METADATA (merged over existing). Parameter-level: PARAM_ARGS_METADATA on (constructor, methodName) via assignMetadata. Property-level (@Client): CLIENT_METADATA=true + CLIENT_CONFIGURATION_METADATA + a null placeholder set directly on the target.

### Decisive source
```ts
// shared disambiguation ladder (identical in MessagePattern and EventPattern):
if ((isNumber(transportOrExtras) || isSymbol(transportOrExtras)) && isNil(maybeExtras)) {
  transport = transportOrExtras;
} else if (isObject(transportOrExtras) && isNil(maybeExtras)) {
  extras = transportOrExtras;
} else {
  transport = transportOrExtras as Transport | symbol;
  extras = maybeExtras!;
}
Reflect.defineMetadata(PATTERN_METADATA, ([] as any[]).concat(metadata), descriptor.value);
Reflect.defineMetadata(PATTERN_HANDLER_METADATA, PatternHandler.MESSAGE, descriptor.value);
Reflect.defineMetadata(TRANSPORT_METADATA, transport, descriptor.value);
Reflect.defineMetadata(PATTERN_EXTRAS_METADATA,
  { ...Reflect.getMetadata(PATTERN_EXTRAS_METADATA, descriptor.value), ...extras },
  descriptor.value);   // stackable decorators accumulate

// gRPC family = MessagePattern wrappers differing only in the streaming dimension:
export function createGrpcMethodMetadata(target, key, service, method, streaming = NO_STREAMING) {
  if (!service) return { service: target.constructor.name, rpc: capitalizeFirstLetter(key), streaming };
  if (service && !method) return { service, rpc: capitalizeFirstLetter(key), streaming };
  return { service, rpc: method, streaming };
}

// GrpcStreamMethod wraps the handler to release the drain buffer after it returns:
descriptor.value = function (this: any, observable: any, ...args: any[]) {
  const result = originalMethod.apply(this, [observable, ...args]);
  const isPromise = result && typeof result.then === 'function';
  if (isPromise) return result.then((data: any) => { observable?.drainBuffer?.(); return data; });
  observable?.drainBuffer?.();
  return result;
};
// then copies EVERY Reflect metadata key from originalMethod onto the wrapper
```

**Flow:** decorator runs at class-definition time ⇒ four keys land on the method value ⇒ ListenerMetadataExplorer (listener-registration-pipeline capsule) gates on PATTERN_HANDLER_METADATA, reads the patterns array / optional TRANSPORT pin / extras ⇒ registers against matching servers. GrpcMethod/GrpcStreamMethod/GrpcStreamCall all delegate to MessagePattern(metadata, Transport.GRPC) with streaming NO_STREAMING/RX_STREAMING/PT_STREAMING respectively — the streaming type is what makes them distinct routes in the gRPC registry (grpc-route-registry-parallel capsule). @Payload/@Ctx write PARAM_ARGS_METADATA entries consumed by RpcContextCreator (rpc-context-creator-args-ladder capsule); @Payload disambiguates propertyKey(string) vs pipes(rest) vs ParameterDecoratorOptions({pipes, schema}).
**Invariant:** PATTERN_METADATA is always an array even for one pattern (the pipeline iterates it); PATTERN_EXTRAS merges over prior values so stacked decorators accumulate rather than clobber; the gRPC name derivation is CLASS-NAME + CAPITALIZED-METHOD-NAME when args are omitted (spec pins all three derivation arms for all three gRPC decorators); the GrpcStreamMethod wrapper must keep a non-Promise Observable return non-thenable (spec pins `not.toHaveProperty('then')`) and must copy all original metadata or pipes/guards would be lost.
**Probe:** `packages/microservices/test/decorators/message-pattern.decorator.spec.ts` (overload matrix pins all four argument shapes + extras merge; GrpcMethod/GrpcStreamMethod/GrpcStreamCall each pin the three derivation arms + non-thenable wrapper), `event-pattern.decorator.spec.ts` (same matrix + multi-pattern array), `payload.decorator.spec.ts` (pins "should not confuse a pipe instance with options": ValidationPipe instance ⇒ pipes length 1, data/schema undefined).
**Runner caveat:** repo deps uninstalled (vitest blocked); expectations quoted from spec sources read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", file_pattern: "message-pattern.decorator.ts", fields: ["lines"], limit: 40 });
// expected @ pin: MessagePattern 37-93, GrpcStreamMethod 126-179, createGrpcMethodMetadata 210-229
await mcp.codebase_memory.search_graph({ project: "nest", qn_pattern: ".*microservices.decorators.*PATTERN_HANDLER_METADATA", limit: 10 });
```

## Verdict
Adopt the four-key split (patterns-array / handler-kind gate / transport pin / merged extras) as the minimal metadata contract for decorator-declared routes — the handler-kind key is what lets one scanner distinguish fan-out events from last-write-wins messages. Adopt the type-based overload ladder (number|symbol ⇒ transport, object ⇒ extras) only when you must support both positions; a single fixed position is simpler. Adapt the gRPC class-name/capitalized-method derivation to your framework's naming conventions; omit it entirely for non-RPC transports. Keep the metadata-copy step whenever you wrap a decorated method — losing PARAM_ARGS_METADATA silently breaks argument extraction.
