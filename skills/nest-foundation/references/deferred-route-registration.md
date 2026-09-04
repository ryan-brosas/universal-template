<!-- capsule-v2 -->
# RouterExplorer deferred registration — how does route collection separate from route installation?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** How can a router emit fully-built route descriptors without registering them, so a caller can sort first — and what metadata must survive the deferral?

## applyCallbackToRouter / onRouteResolved / registerResolvedRoute / copyMetadataToCallback
**Path/Symbol:** `packages/core/router/router-explorer.ts:applyCallbackToRouter` (:164-302), `registerResolvedRoute` (:310-332), `copyMetadataToCallback` (:510-522), `createRequestScopedHandler` (:437-487).
**Signature:** `options: { onRouteResolved?, deferRegistration? = false }`; `onRouteResolved(route: ResolvedRoute): void` carries `{method, path (normalized), rawPath, host, version, methodVersion, controllerVersion, handler, targetCallback, methodName, instanceWrapper}`.
**Data Shape:** ResolvedRoute is the COMPLETE install unit — registration later needs nothing beyond it.

### Decisive source
```ts
const { onRouteResolved, deferRegistration = false } = options;
if (!deferRegistration) {
  this.copyMetadataToCallback(targetCallback, routeHandler);
  routerMethodRef(normalizedPath, routeHandler);        // classic path
}
onRouteResolved?.({ method, path: normalizedPath, rawPath: path,
                    handler: routeHandler, targetCallback, ... });

// later, caller-chosen order:
public registerResolvedRoute(router, route) {
  this.copyMetadataToCallback(route.targetCallback, route.handler);
  routerMethodRef(route.path, route.handler);
}

private copyMetadataToCallback(originalCallback, targetCallback) {
  for (const key of Reflect.getMetadataKeys(originalCallback))
    Reflect.defineMetadata(key, Reflect.getMetadata(key, originalCallback), targetCallback);
}
```

**Flow:** per-routeDefinition → request-scoped? build lazy per-request handler : build static callback proxy → host filter wrap → version filter wrap (non-URI versioning) → either register immediately OR publish to `onRouteResolved` → application (`routes-resolver.ts` + router-module) collects all routes, runs RouteSpecificitySorter, filters sort-resolved shadows via RouteConflictDetector, then installs each through `registerResolvedRoute`.
**Invariant:** (1) `copyMetadataToCallback` must run at INSTALL time regardless of path taken — the proxy chain creates NEW functions and Reflect metadata (route args, guards, interceptors keys) lives on the ORIGINAL callback; skipping the copy breaks every param-decorator lookup. (2) `rawPath` is preserved separately from the normalized registered path — conflict detection tokenizes the raw grammar while the adapter gets the normalized one. (3) The request-scoped error path caches exception filters in a WeakMap keyed by the UNBOUND method (`exceptionFiltersCache.get(instance[methodName])`) — keying by bound fn would leak per request.
**Probe:** `packages/core/test/router/router-explorer.spec.ts::copyMetadataToCallback` (:250 "should copy the metadata from the original callback to the target callback"), createRequestScopedHandler error delegation :204.
**Coverage caveat:** end-to-end deferred-registration ordering exercised at integration level; unit specs pin metadata copying + scoped-handler error routing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "RouterExplorer deferRegistration onRouteResolved registerResolvedRoute copyMetadataToCallback", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt resolve-then-install separation for any router that needs pre-registration passes (sorting, conflict linting, graph inspection); adapt the descriptor fields; omit the dual-path when no sorting exists. Porting wrong: dropping metadata copy on the deferred branch (params/guards silently vanish), or conflating normalizedPath with rawPath across the two consumers.
