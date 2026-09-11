<!-- capsule-v2 -->
# gRPC client service factory — how does a dynamically loaded proto client become an Rx surface with correct cancel semantics when the base ClientProxy API must stay unusable?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How do you expose typed proto stubs as Observables with per-call cancellation ladders while making every inherited message-client method fail loudly instead of silently misbehaving?

## Inverted inheritance: throw on the inherited surface, expose getService
**Path/Symbol:** `packages/microservices/client/client-grpc.ts:ClientGrpcProxy` (31-400) — `getService` (66-80), `createClientByServiceName` (86-120), `createStreamServiceMethod` (162-223), `createUnaryServiceMethod` (225-291); throws at 359-399.
**Signature:** `getService<T extends object>(name: string): T`; `createServiceMethod(client, methodName): (...args) => Observable<unknown>`.
**Data Shape:** `clients = Map<serviceName, grpcClient>` memoization; `grpcClients` = loaded proto packages; wrappers close over the native stub and its `{requestStream?, responseStream?}` booleans; sentinel `GRPC_CANCELLED = 'Cancelled'`.

### Decisive source
```ts
// every inherited entry point throws (each individually spec-pinned):
public async connect() { throw new Error('The "connect()" method is not supported in gRPC mode.'); }
public send(...)      { throw new Error('Method is not supported in gRPC mode. ...'); }
protected publish(packet, callback): any { throw new Error('...'); }

// the real API — per-service memoized stub + wrapped prototype methods:
public getService<T extends object>(name: string): T {
  const grpcClient = this.getClientByServiceName(name);        // memoized in this.clients
  const clientRef = this.getClient(name);
  if (!clientRef) throw new InvalidGrpcServiceException(name);
  const protoMethods = Object.keys(clientRef[name].prototype);
  const grpcService = {} as T;
  protoMethods.forEach(m => { grpcService[m] = this.createServiceMethod(grpcClient, m); });
  return grpcService;
}
```

```ts
// stream wrapper teardown + cancel ladder:
call.on('error', (error: any) => {
  if (error.details === GRPC_CANCELLED) {
    call.destroy();
    if (isClientCanceled) return;          // our own cancel ⇒ swallow, no observer.error
  }
  observer.error(this.serializeError(error));
});
call.on('end', () => {
  if (upstreamSubscription) { upstreamSubscription.unsubscribe(); upstreamSubscription = null; }
  call.removeAllListeners();
  observer.complete();
});
return () => {
  if (upstreamSubscription) { upstreamSubscription.unsubscribe(); upstreamSubscription = null; }
  if (call.finished) return undefined;
  isClientCanceled = true;
  call.cancel();
};
```

**Flow:** constructor loads proto synchronously (`createClients`) → first `getService(name)` lazily constructs and memoizes `new clientRef[name](url, credentials, options)` → every prototype method becomes a COLD Observable: subscribe opens exactly one call; an Observable first argument is detected via `isFunction(arg.subscribe)` and treated as a request-stream source pumped through its own subscription (`next→call.write`, `error→call.emit('error')`, `complete→call.end`); unary responses resolve via callback (`next`+`complete`) or `observer.error(serializeError(err))`. Unsubscribe tears down upstream first, then cancels unfinished calls through the latch so the subsequent `'Cancelled'` server error is destroyed-and-swallowed rather than double-reported.
**Invariant:** one subscription = one gRPC call; post-unsubscribe handler invocations emit NOTHING; real server errors propagate even after `finished` flips (only cancel-caused errors are swallowed); `close()` closes each memoized stub (guarded by `isFunction(client.close)`) then clears both caches.
**Probe:** `packages/microservices/test/client/client-grpc.spec.ts` flow-control blocks: "propagates server errors" (`data a,b` then error with `finished=true`, `cancel` NOT called), "handles client side cancel" (unsubscribe → `cancel`+`destroy` called, later `{details:'Cancelled'}` produces NO `errorSpy` call), unary "should cancel call on client unsubscribe" (post-unsubscribe handler emits nothing), plus individual throw-pins for send/publish/dispatchEvent/connect.
**Runner caveat:** direct test execution blocked (deps uninstalled); expectations quoted from spec source read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", name_pattern: "createStreamServiceMethod|createUnaryServiceMethod", fields: ["lines"], limit: 10 });
// live @ pin: ClientGrpcProxy.createStreamServiceMethod 162-223 / createUnaryServiceMethod 225-291 (server twins listed separately)
await mcp.codebase_memory.trace_path({ project: "nest", function_name: "nest.packages.microservices.client.client-kafka.ClientKafka.createResponseCallback", direction: "outbound", depth: 2 });
// contrast trace: sibling transports resolve their OWN response callbacks — gRPC has none to trace
```

## Verdict
Adopt the inverted-inheritance guardrail verbatim whenever a transport's native API replaces the generic publish/correlate loop — failing loudly beats a silently wrong generic path; adopt the cancel ladder (`details==='Cancelled'` OR unary `code===1`, `isClientCanceled` latch, `finished` skip) for any streaming RPC bridge; adapt the upstream-pump triple (`write/emit/end`) to your reactive library's subject semantics. Omit the per-service memoization only if your runtime recreates channels cheaply — but keep close()-clears-cache symmetry.
