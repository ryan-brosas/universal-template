<!-- capsule-v2 -->
# Internal core module — how are framework-internal services exposed as ordinary injectables without polluting user modules?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How does the REQUEST token become injectable, and why do internal providers use factories over the container?

## InternalCoreModule + factory
**Path/Symbol:** `packages/core/injector/internal-core-module/internal-core-module.ts` (1-38); `internal-core-module-factory.ts:InternalCoreModuleFactory.create` (10-52); `packages/core/injector/container.ts:registerCoreModuleRef` (348-351).
**Signature:** `InternalCoreModule.register(providers): DynamicModule`; `InternalCoreModuleFactory.create(container, scanner, moduleCompiler, httpAdapterHost, graphInspector, moduleOverrides?)`.
**Data Shape:** providers array of Value/Factory/Existing provider records; exports = same tokens.

### Decisive source
```ts
@Global()
@Module({
  providers: [Reflector, ReflectorAliasProvider, requestProvider, inquirerProvider],
  exports:   [Reflector, ReflectorAliasProvider, requestProvider, inquirerProvider],
})
export class InternalCoreModule {
  static register(providers) {
    return { module: InternalCoreModule, providers: [...providers], exports: [...providers.map(i => i.provide)] };
  }
}

// factory wiring — closures over the ONE container instance
{ provide: ModulesContainer, useFactory: () => container.getModules() },
{ provide: HttpAdapterHost,  useFactory: () => httpAdapterHost },
{ provide: LazyModuleLoader, useFactory: lazyModuleLoaderFactory },  // builds its OWN Injector+InstanceLoader
```

**Flow:** scanner.scan() → registerCoreModule FIRST (so it occupies modules index 0; root module is second — `calculateModulesDistance` and `selectContextModule` both rely on this ordering) → container.registerCoreModuleRef stores it → REQUEST provider instances get set per-context by `registerRequestProvider`.
**Invariant:** The module is `@Global()` so Reflector/REQUEST/INQUIRER resolve everywhere without imports. It must be the FIRST registered module (distance/hook ordering and context-module selection depend on it). The alias pattern `{ provide: Reflector.name, useExisting: Reflector }` exposes string-token lookup for the same singleton.
**Probe:** `packages/core/test/injector/internal-core-module/*.spec.ts` + registration-order dependence in `packages/core/test/scanner.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "InternalCoreModuleFactory register requestProvider global", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt a hidden global bootstrap module carrying framework services with container-closure factories; adapt the service set to your framework's needs; omit the preview allowlist side effect. Porting wrong: registering internals after user modules breaks distance-based hook ordering and root-module detection.
