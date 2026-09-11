<!-- capsule-v2 -->
# Lifecycle hooks — in what order do init/destroy/shutdown hooks run across modules and instances?

**Source:** nest MIT `master@61b03510`; Codebase Memory `nest`. **Question:** What ordering guarantees must a ported lifecycle runner reproduce exactly?

## NestApplicationContext hook runners
**Path/Symbol:** `packages/core/nest-application-context.ts:init` (251-262), `close` (268-276), `callInitHook` (419-424), `callDestroyHook` (430-438), `getModulesToTriggerHooksOn` (487-501); `packages/core/hooks/on-module-init.hook.ts:callModuleInitHook` (33-60).
**Signature:** `getModulesToTriggerHooksOn(): Module[]` — sorted `b.distance - a.distance`, cached in `_moduleRefsForHooksByDistance`.
**Data Shape:** module distance: graph depth from root; globals pinned at `Number.MAX_VALUE`.

### Decisive source
```ts
// modules: FARTHEST first (descending distance); destroy/shutdown = same list REVERSED
const compareFn = (a, b) => b.distance - a.distance;
...
// inside one module — hierarchy levels, shallowest first, then the module itself LAST
const [_, moduleClassHost] = providers.shift()!;   // self provider is always first entry
for (const level of levels) await Promise.all(callOperator(groupedInstances.get(level)!));
if (moduleClassInstance && hasOnModuleInitHook(moduleClassInstance)
    && moduleClassHost.isDependencyTreeStatic()) {
  await moduleClassInstance.onModuleInit();        // module class init runs AFTER its members
}
```

**Flow:** init = callInitHook → callBootstrapHook (`await this.initializationPromise` guards re-entry). close = prepareClose → callDestroyHook → callBeforeShutdownHook → dispose → callShutdownHook → unsubscribe signals. Signal-driven cleanup ignores subsequent signals while shutting down (`receivedSignal` latch), then re-raises via `process.kill(process.pid, signal)` unless `useProcessExit`.
**Invariant:** Init order: global modules (MAX distance) → deeper modules before shallower → within a module, dependencies by hierarchy level → module class last. Destroy/shutdown run the exact reverse. Aliased providers are skipped (`getNonAliasProviders`) so hooks fire once per instance.
**Probe:** `packages/core/test/nest-application-context.spec.ts` + `packages/core/test/hooks/*.spec.ts`.
**Coverage caveat:** none recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nest", query: "callInitHook callDestroyHook getModulesToTriggerHooksOn distance", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt distance-descending module order with per-module hierarchy-level fan-out and exact reversal for teardown; adapt hook names to your framework; omit signal re-raise mechanics if you have a dedicated shutdown coordinator. Porting wrong: running module-class hooks before their members breaks every constructor-time assumption an onModuleInit makes.
