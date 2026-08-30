<!-- capsule-v2 -->
# Microservice listen/init lazy boot — what starts when, and what does preview mode deliberately skip?

**Source:** nest (MIT) `master@4c38a5ab100f`; Codebase Memory `nest`. **Question:** How does a microservice application defer ALL wiring (socket module, client binding, listener registration) until first use, and how do global-enhancer registrations enforce their before-init window?

## listen() boots-if-needed then wraps the server callback; preview gates wiring
**Path/Symbol:** `packages/microservices/nest-microservice.ts:NestMicroservice.listen` (285-301), `init` (268-278), `registerModules` (113-134), `loadSocketModule` (407-417); enhancer warn latches `useGlobalFilters/useGlobalPipes/useGlobalInterceptors/useGlobalGuards/registerPreRequestHook` (165-266).
**Signature:** `listen(): Promise<any>`; `init(): Promise<this>`; `registerModules(): Promise<any>`.
**Data Shape:** latches `isInitialized`, `wasInitHookCalled`; `microserviceConfig.autoFlushLogs` (default true via `?? true`).

### Decisive source
```ts
public async listen(): Promise<any> {
  this.assertNotInPreviewMode('listen');
  !this.isInitialized && (await this.registerModules());   // lazy boot at first use
  return new Promise((resolve, reject) => {
    this.serverInstance.listen((err, info) => {
      if (this.microserviceConfig?.autoFlushLogs ?? true) this.flushLogs();
      if (err) return reject(err as Error);
      this.logger.log(MESSAGES.MICROSERVICE_READY);
      resolve(info);                                       // broker's bind info to caller
    });
  });
}
public async init() {
  if (this.isInitialized) return this;
  await this.loadSocketModule();      // optionalRequire('@nestjs/websockets/socket-module')
  await super.init();
  await this.registerModules();
  return this;
}
public async registerModules() {
  await this.loadSocketModule();
  this.socketModule && (await this.socketModule.register(container, appConfig, graphInspector, appOptions));
  if (!this.appOptions.preview) {     // PREVIEW: skip client + listener wiring entirely
    this.microservicesModule.setupClients(this.container);
    this.registerListeners();
  }
  this.setIsInitialized(true);
  if (!this.wasInitHookCalled) { await this.callInitHook(); await this.callBootstrapHook(); }
}
```

**Flow:** construction only registers the module context and builds the server instance; everything expensive waits. First `init()` or `listen()` triggers `registerModules`: optional websockets module loaded via `optionalRequire` (ESM-safe, absent ⇒ skipped silently), gateways registered, THEN clients bound to `@Client`-decorated properties and pattern handlers registered against the transport — unless `preview` mode is on, which produces a scan-only application that can be introspected but refuses `listen` (`assertNotInPreviewMode`). The server's callback-style `listen(err, info)` is wrapped into a promise where `info` (broker bind address) becomes the resolution value; log flushing after bind respects `autoFlushLogs ?? true`. Every global-enhancer setter and `registerPreRequestHook` warns when `isInitialized` is already true — registration must precede init because listeners snapshot globals at proxy-build time.
**Invariant:** idempotency — repeated `init()` returns `this` without re-running; init/bootstrap hooks fire exactly once per process (`wasInitHookCalled` latch shared with the constructor-time flag setter); a failed server bind rejects the SAME promise that `listen()` returned rather than throwing inside a callback.
**Probe:** `packages/microservices/test/nest-microservice.spec.ts` (strategy `listen` spy called exactly once by `instance.listen()`; post-init `registerPreRequestHook` triggers logger.warn spy; hook registration returns `this` for chaining).
**Runner caveat:** direct spec execution blocked (root deps uninstalled); expectations quoted verbatim from the spec source read directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "microservice listen register modules initialized preview", limit: 10 });
// live @ pin: NestMicroservice methods rank top of the microservices group
await mcp.codebase_memory.get_code_snippet({ project: "nest", qualified_name: "nest.packages.core.nest-application-context.NestApplicationContext.init" });
// live @ pin: base init (251-262) — initializationPromise composition the subclass awaits
```

## Verdict
Adopt construct-cheap/boot-lazy with a single registerModules funnel and preview-mode scan-only gating for any embeddable application shell. Adapt the optional-module loader to your runtime's dynamic import story. Omit the enhancer warn latches only if your enhancers are re-read per request instead of snapshotted at wiring time.
