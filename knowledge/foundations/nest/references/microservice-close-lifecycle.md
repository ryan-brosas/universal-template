<!-- capsule-v2 -->
# Microservice close lifecycle — in what order do transport, clients, hooks, and signals tear down, and what stops double-close?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** When a microservice application closes, who stops the transport, who closes the injected `@Client` proxies, and how does the same code path survive both explicit `close()` and signal-driven shutdown?

## Transport first, latch second, module closes clients in parallel
**Path/Symbol:** `packages/microservices/nest-microservice.ts:NestMicroservice.close` (308-315) + `closeApplication` (373-379) + `dispose` override (381-388) + `createServer` (81-111); `packages/microservices/microservices-module.ts:MicroservicesModule.close` (123-127); base chain `packages/core/nest-application-context.ts:NestApplicationContext.close` (268-276); strategy fallback `packages/microservices/server/server-factory.ts:ServerFactory.create` (20-43).
**Signature:** `close(): Promise<any>`; `closeApplication(): Promise<any>`; `MicroservicesModule.close(): Promise<void>`.
**Data Shape:** state latches `isTerminated`, `wasInitHookCalled`; `serverInstance: Server`; `clientsContainer` append-only list.

### Decisive source
```ts
public async close(): Promise<any> {
  await this.serverInstance.close();     // transport STOPS FIRST — no new work mid-teardown
  if (this.isTerminated) return;         // idempotency latch AFTER transport close
  this.setIsTerminated(true);
  await this.closeApplication();
}
protected async closeApplication() {
  this.socketModule && (await this.socketModule.close());
  this.microservicesModule && (await this.microservicesModule.close());
  await super.close();                   // NestApplicationContext.close chain
  this.setIsTerminated(true);
}
// MicroservicesModule — the pass-5 open question "who closes clients?" answered:
public async close() {
  const clients = this.clientsContainer.getAllClients();
  await Promise.all(clients.map(client => client.close()));   // PARALLEL
  this.clientsContainer.clear();
}
```

**Flow:** explicit path = transport close → latch → socketModule → microservicesModule (all `@Client` proxies closed concurrently, container cleared) → base `super.close()` which awaits `initializationPromise`, then prepareClose (base noop — NestMicroservice does NOT override it), callDestroyHook, callBeforeShutdownHook(signal), dispose, callShutdownHook, unsubscribeFromProcessSignals. The subtle piece: because `close()` latched `isTerminated` BEFORE `super.close()` runs, the NestMicroservice `dispose` OVERRIDE — whose body would close server+socket+microservices AGAIN — returns immediately at its own `if (this.isTerminated) return;`. That override exists for the SIGNAL path, where the process-signal listener calls the base `close(signal)` directly and `dispose` is the only place transport teardown happens. Construction-side mirror: `microservicesModule.register` → `createServer(config)` (strategy beats factory: `'strategy' in config/resolvedConfig ⇒ serverInstance = strategy`, else `{transport: TCP, ...config}` spread into `ServerFactory.create`, whose switch maps REDIS/NATS/MQTT/GRPC/KAFKA/RMQ and defaults unknown transports to ServerTCP) → `addRpcTarget(serverInstance)` into the modules container.
**Invariant:** the transport must close before any hook can observe teardown (no new messages race destroy hooks); client closing is concurrent, not sequential — one hung broker connection cannot serialize the shutdown of the others; `isTerminated` must be set before `super.close()` so the dispose override's guard suppresses duplicate teardown on the explicit path while still arming the signal path.
**Probe:** `packages/microservices/test/nest-microservice.spec.ts` (`{transport: TCP}` + no strategy ⇒ `serverInstance instanceof ServerTCP`; `{strategy}` ⇒ exact same instance returned; `useFactory` returning `{strategy}` ⇒ same instance — all three arms pinned; `registerPreRequestHook` post-init warns; `getTransportServer()` returns the strategy). `packages/microservices/test/container.spec.ts` pins ClientsContainer add/getAll/clear (the container itself stays lifecycle-free).
**Runner caveat:** direct spec execution blocked (root deps uninstalled); expectations quoted verbatim from the spec sources read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "nest", function_name: "nest.packages.microservices.nest-microservice.NestMicroservice.close", direction: "both", depth: 2 });
// live @ pin: callees {closeApplication, setIsTerminated, MicroservicesModule.close}; zero graph callers (entry point)
await mcp.codebase_memory.search_graph({ project: "nest", query: "microservice close application context clients container terminate", limit: 15 });
// live @ pin: rank#1/#2/#5 NestApplicationContext.close(268-276)/NestMicroservice.closeApplication(373-379)/NestMicroservice.close(308-315)
```

## Verdict
Adopt the ordering contract (transport-first, latch-before-base-chain, parallel client drain with container clear, guard-armed dispose for the signal twin-path). Adapt which modules sit between transport close and the base chain to your framework's optional subsystems. Omit the dispose-override guard only if your framework has exactly one shutdown entry point.
