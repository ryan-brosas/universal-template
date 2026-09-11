<!-- capsule-v2 -->
# RoutesResolver boot wiring — not-found handler, error-handler translation, module-path metadata with app-id suffix

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What does the router register BEFORE any route, and why is MODULE_PATH looked up twice?

## registerNotFoundHandler / registerExceptionHandler / getModulePathMetadata
**Path/Symbol:** `packages/core/router/routes-resolver.ts:registerNotFoundHandler` (:155-167), `registerExceptionHandler` (:169-188), `getModulePathMetadata` (:190-197).
**Signature:** `registerNotFoundHandler(): void` (throws NotFoundException `Cannot ${method} ${url}` through the filter stack); `getModulePathMetadata(metatype): string | undefined`.
**Data Shape:** both handlers are built from `{}` instance + callback via RouterExceptionFilters.create + RouterProxy — i.e., they get the FULL filter stack, not raw responses.

### Decisive source
```ts
private getModulePathMetadata(metatype: Type<unknown>): string | undefined {
  const modulesContainer = this.container.getModules();
  const modulePath = Reflect.getMetadata(
    MODULE_PATH + modulesContainer.applicationId, metatype);   // app-scoped key first
  return modulePath ?? Reflect.getMetadata(MODULE_PATH, metatype);
}
```

**Flow:** resolve() iterates ALL modules → per controller reads host/version/module-path metadata → extractRouterPath (leading-slash normalized, array paths supported, UnknownRequestMappingException when PATH_METADATA missing) → routerExplorer.explore per path → after all routes: registerNotFoundHandler wires a 404 that THROWS NotFoundException so custom filters and response shaping still apply; registerExceptionHandler maps framework-layer errors into the filter world.
**Invariant:** The 404 path goes through exception filters ON PURPOSE — users can intercept it. MODULE_PATH resolution prefers the applicationId-suffixed key because multiple Nest apps can share a process; the bare fallback keeps cross-app imports working. Version metadata falls back to versioningConfig.defaultVersion when a controller declares none.
**Probe:** `packages/core/test/router/routes-resolver.spec.ts` (module iteration + handler registration); app-scope suffix contract pinned at `packages/core/injector` applicationId stamping.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RoutesResolver registerNotFoundHandler registerExceptionHandler getModulePathMetadata", limit: 5 });
```

## Verdict
Adopt throwing-not-found routed through filters and the suffixed-metadata lookup for multi-app hosts; adapt messages/keys to your conventions; omit if single-app. Porting wrong: registering a raw 404 responder bypasses every user filter, and dropping the app-id suffix breaks nested/multi-app module path resolution.
