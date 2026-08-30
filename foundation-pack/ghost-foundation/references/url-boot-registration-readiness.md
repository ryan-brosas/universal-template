<!-- capsule-v2 -->
# Boot registration & readiness gate — how does the URL service come alive, survive route reloads, and hold the site during the gap?

**Source:** Ghost MIT `main@81292b004cf59591f03d7dbe01f28f31c09ee813`; Codebase Memory project `ghost`. **Question:** Who constructs the service, when do routers register, what must happen on backend-only boots and routes.yaml reloads, and what do users see while routing is unready?

## Singleton composition + routersReady maintenance gate
**Path/Symbol:** `ghost/core/core/server/services/url/index.js` (singleton, 7 lines); `ghost/core/core/boot.js:initExpressApps` (:242–264) + `initDynamicRouting` (:279–312); `ghost/core/core/frontend/services/routing/router-manager.js:routerCreated` (:32–53), `start` (:101–164), `handleTimezoneEdit` (:173–202); readiness consumer `ghost/core/core/app.js:isMaintenanceModeEnabled/maintenanceMiddleware` (:14–38).
**Signature:** `onRouterAddedType(identifier: string, filter: string | null, resourceType: string, permalink: string): void`; `reset(): void`; `hasFinished(): boolean`; constructor requires `findResource` else throws `IncorrectUsageError`.
**Data Shape:** One process-wide instance (`module.exports = new LazyUrlService({ findResource: createFindResource(models) })`) shared by frontend app, API serializers and RouterManager; `routersReady` flips true on first registration.

### Decisive source
```js
// boot.js initDynamicRouting — runs on every boot:
//   "The APIs, the email service and webhooks all build URLs, so a
//    backend-only boot that skipped this resolved every resource to /404/."
if (!frontend) {
  routing.routerManager.init({ urlService }); // same init, express router discarded
}
await routeSettingsModule.service.start({ routerManager: routing.routerManager, urlService });
```
```js
// app.js — hasFinished() gates the whole site:
if (req.app.get('maintenance') || config.get('maintenance').enabled || !urlService.hasFinished()) { ... }
res.writeHead(503, { 'content-type': 'text/html' });          // maintenance.html
res.set({ 'Cache-Control': 'no-cache, private, no-store, must-revalidate, ...' });
```
**Flow:** boot requires singleton → RouterManager.init resets registries, emits RoutesReset → routers built in documented precedence order (unsubscribe/email → preview → static routes → taxonomies → collections → static pages → apps) → each router with permalinks calls `onRouterAddedType(identifier, filter, resourceType, permalinkValue)` (static-routes router skipped: no permalinks ⇒ no resource URLs) → `hasFinished()` true lifts the maintenance 503. Route reload: configs reset, window re-gates. Timezone edit calls `onRouterUpdated()` ONLY when the collection permalink contains `:year|:month|:day`.
**Invariant:** Registration ORDER is ownership priority; a backend-only boot MUST still run dynamic routing or every API-built URL resolves to /404/; the maintenance middleware treats not-ready exactly like explicit maintenance mode (503 + no-store so caches don't pin the outage page); `reset()` clears configs, relation memo, readiness AND thin-resource counters together.
**Probe:** `ghost/core/test/unit/server/services/url/lazy-url-service.test.js` pins `"is not finished before any router is registered"`, `"is not finished again after a reset (route-reload window)"`, `"throws when constructed without a findResource hook"`; `ghost/core/test/unit/frontend/services/routing/router-manager.test.js` pins `"emits RoutesReset once per init, before any router registers"` and `"emits a null path for routers that have no index route"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ghost", query: "onRouterAddedType RouterManager routerCreated", limit: 10 });
// observed at pin: RouterManager.routerCreated rank #1 (router-manager.js:32-53),
// LazyUrlService.onRouterAddedType rank #2 (lazy-url-service.ts:228-244)
```

## Verdict
Adopt singleton-with-injected-hooks construction, register-on-create with skip rules for non-resource routers, readiness flag gating site availability, and reload-as-reset. Adapt the precedence ladder to your route kinds; omit Ghost's timezone special-case if your permalinks never embed dates (or generalize it to any config that shifts generated paths).
