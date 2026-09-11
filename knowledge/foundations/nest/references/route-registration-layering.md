<!-- capsule-v2 -->
# RouterExplorer registration pipeline — scoped-handler fork, host filter, version filter, deferred install, adapter-verb fallback

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What is the full path from a scanned route definition to a live adapter route, and which wrapper layers wrap in which order?

## applyCallbackToRouter layering
**Path/Symbol:** `packages/core/router/router-explorer.ts:applyCallbackToRouter` (:164-302), `applyHostFilter` (:334-388), `registerResolvedRoute` (:310-332); `packages/core/helpers/router-method-factory.ts:get` (:25-32).
**Signature:** `applyCallbackToRouter(router, routeDefinition, instanceWrapper, moduleKey, routePathMetadata, host, options?)`; `RouterMethodFactory.get(target, requestMethod): Function`.
**Data Shape:** `RouteDefinition = { path: string[], requestMethod, targetCallback, methodName, version? }`; `exceptionFiltersCache: WeakMap` keyed by method function.

### Decisive source
```ts
const isRequestScoped = !instanceWrapper.isDependencyTreeStatic();
const proxy = isRequestScoped
  ? this.createRequestScopedHandler(...)      // per-request context proxy
  : this.createCallbackProxy(...);            // static one-shot composition
let routeHandler = this.applyHostFilter(host, proxy);   // layer 1: hostname gate
paths.forEach(path => {
  if (isVersioned && type !== VersioningType.URI) {
    routeHandler = this.applyVersionFilter(router, meta, routeHandler); // layer 2
  }
  ...
  if (!deferRegistration) {
    this.copyMetadataToCallback(targetCallback, routeHandler);
    routerMethodRef(normalizedPath, routeHandler);       // final install
  }
  onRouteResolved?.({ method, path, rawPath: path, handler, ... }); // deferred handoff
});
```

**Flow:** RouterExecutionContext.create builds the innermost handler → static vs request-scoped fork chooses the proxy → host filter (pathToRegexp over `getRequestHostname`, filling `req.hosts` named captures; no match + no `next` → InternalServerErrorException) → non-URI version filters wrap → metadata copied onto the FINAL wrapped handler so @Reflect metadata survives layering → installed via `routerMethodFactory.get` (REQUEST_METHOD_MAP incl. QUERY/PROPFIND/LOCK; unknown verb falls back to `target.use`) → or handed to `onRouteResolved` for sort-aware deferred registration. Exception filters for the error path are cached per-method in a WeakMap.
**Invariant:** copyMetadataToCallback must run AFTER all wrapping — metadata read back from the registered handler is what middleware introspection sees. Host-filter miss calls `next()` when available but THROWS when not; URI versioning never gets a version filter (paths carry it). Deferred mode separates RESOLVE from INSTALL so specificity sorting can reorder before anything hits the adapter.
**Probe:** `packages/core/test/router/router-explorer.spec.ts` ("should call and return the `applyVersionFilter` from the underlying http server", "should then copy the metadata from the original callback to the target callback").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouterExplorer applyHostFilter routerMethodFactory REQUEST_METHOD_MAP", limit: 5 });
```

## Verdict
Adopt resolve-vs-install separation and post-wrap metadata copying; adapt host/version filtering to your router's native features; omit the verb-fallback only if your adapter guarantees every method. Porting wrong: installing handlers before wrapping loses decorator metadata, and skipping the request-scoped fork binds stale singleton controllers into every request.
