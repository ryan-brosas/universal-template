<!-- capsule-v2 -->
# Bootstrap pipeline — what is the exact scan→instantiate order, and why does it run inside an ExceptionsZone with abort semantics?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What sequence must a porter preserve so the container is fully populated before any instance loads?

## NestFactoryStatic.initialize + ExceptionsZone
**Path/Symbol:** `packages/core/nest-factory.ts:initialize` (212-268), `createApplicationContext` (177-206); `packages/core/errors/exceptions-zone.ts:ExceptionsZone` (1-40).
**Signature:** `initialize(module, container, graphInspector, config?, options?, httpServer?)`; `ExceptionsZone.asyncRun(callback, teardown?, autoFlushLogs)`.
**Data Shape:** teardown defaults to `process.exit(1)`; `abortOnError === false` swaps in `rethrow`.

### Decisive source
```ts
await ExceptionsZone.asyncRun(async () => {
  await dependenciesScanner.scan(module);              // 1. metadata → container records
  await instanceLoader.createInstancesOfDependencies(); // 2. prototypes, then instances
  dependenciesScanner.applyApplicationProviders();      // 3. APP_* globals onto config
}, teardown, this.autoFlushLogs);
...
private handleInitializationError(err: unknown) {
  if (this.abortOnError) process.abort();               // fail fast by default
  rethrow(err);
}
```

**Flow:** set UuidFactory mode (deterministic under `snapshot`) → construct Injector/InstanceLoader/DependenciesScanner → httpServer?.init() → ExceptionsZone wraps the three phases → on error either abort the process or rethrow.
**Invariant:** The three phases are strictly ordered and non-interleaved; scanning must complete for ALL modules before ANY instantiation begins (the loader itself iterates modules concurrently but only after full scan). The app object returned is a Proxy (`createAdapterProxy`) that funnels every method call through ExceptionsZone — error containment is a property of the returned object, not just of init.
**Probe:** `packages/core/test/nest-application.spec.ts` + scanner/instantiation ordering exercised via `packages/core/test/injector/instance-loader.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "NestFactory initialize ExceptionsZone asyncRun abortOnError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt scan-all → instantiate-all → apply-globals as a strict pipeline inside one error boundary; adapt the failure policy (abort vs rethrow) to your host; omit the adapter Proxy if you have no mixed HTTP surface. Porting wrong: instantiating while still scanning yields UnknownModuleException storms because provider tokens aren't registered yet.
