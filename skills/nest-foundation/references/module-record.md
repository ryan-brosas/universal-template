<!-- capsule-v2 -->
# Module record — what does a Module own, and why do transient/request-scoped providers skip re-registration?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What per-module state must a porter replicate so exports validation and scope semantics behave identically?

## Module
**Path/Symbol:** `packages/core/injector/module.ts:Module` (core providers 168-214, addProvider 251-292, validateExportedProvider 495-511, createModuleReferenceType 613-665).
**Signature:** `addProvider(provider): InjectionToken`; `validateExportedProvider(token): InjectionToken`; `addImport(moduleRef: Module)` (a `Set<Module>`, not token set).
**Data Shape:** five collections — `_providers`, `_injectables`, `_middlewares`, `_controllers` (all `Map<InjectionToken, InstanceWrapper>`), `_exports` (Set<token>) — plus `_distance`, `_isGlobal`, `_entryProviderKeys`.

### Decisive source
```ts
// every module silently gets three core providers
public addCoreProviders() {
  this.addModuleAsProvider();   // the module class itself is injectable (instance: null until init)
  this.addModuleRef();          // a PRE-RESOLVED per-module ModuleRef subclass
  this.addApplicationConfig();  // pre-resolved shared ApplicationConfig
}

// re-registering the same class under TRANSIENT/REQUEST scope is a no-op...
if ((this.isTransientProvider(provider) || this.isRequestScopeProvider(provider)) && isAlreadyDeclared) {
  return provider;
}
// ...because scoped instances live in InstanceWrapper context maps, not in this Map

// exports must be a local provider OR come from a direct import
if (!imports.includes(token as Type<unknown>)) {
  throw new UnknownExportException(providerName, name);
}
```

**Flow:** construct → addCoreProviders → scanner fills providers/controllers/exports → imports accumulate as Module refs.
**Invariant:** The self provider is registered with `isResolved: false, instance: null` and only materializes during instantiation (`get instance` throws RuntimeException before that; `isInstantiated` checks it). Export validation is eager at declaration time. `createModuleReferenceType()` closes over `self` to build a per-module `ModuleRef` whose default `strict: true` scopes lookups by `self.id`.
**Probe:** `packages/core/test/injector/module.spec.ts` + `packages/core/test/injector/module-ref.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "Module addProvider validateExportedProvider core providers", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the module-record shape (providers/controllers/exports + implicit self/ModuleRef/config providers); adapt the ModuleRef closure factory if your lookup API differs; omit middleware collection when not porting the HTTP layer. Porting wrong: treating export validation as lazy makes broken graphs surface at resolution time with worse errors.
