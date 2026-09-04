<!-- capsule-v2 -->
# Noop-default DI registration — how does optional infrastructure stay optional without null checks everywhere?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How are analyzer/worker/projection dependencies wired so the package boots with zero adapters and upgrades in place when a real one registers later?

## isRegistered-gated defaults + class-token projection + interval runners
**Path/Symbol:** `packages/v2/table-query-ops/src/di.ts`: `registerV2TableOps` (:41-141, defaults :97-116: analyzer `enabled:false/intervalMs:60_000/lookbackMs:900_000/batchSize:100`, taskWorker `enabled:false/allowedKinds:['manual_investigation']/allowManualIndexExecution:false`); `tokens.ts`: `v2TableOpsTokens` (23L symbol registry).
**Signature:** `registerV2TableOps(container, options?): DependencyContainer` — returns the SAME container for chaining.
**Data Shape:** every default wrapped in `if (!container.isRegistered(token))`; handlers registered LAST and UNCONDITIONALLY; the projection is registered under its own CLASS token (not a symbol) because @ProjectionHandler decorates the class.

### Decisive source
```ts
// The projection is registered into the global event bus by @ProjectionHandler on
// package import. Always wire a scheduler + the class token so field events never
// hit "unregistered dependency" when table-query-ops postgres adapters are off.
if (!container.isRegistered(v2TableOpsTokens.searchVectorSchemaMaintenanceScheduler)) {
  container.register(v2TableOpsTokens.searchVectorSchemaMaintenanceScheduler,
                    NoopTableSearchVectorSchemaMaintenanceScheduler, { lifecycle });
}
if (!container.isRegistered(TableSearchVectorSchemaMaintenanceProjection)) {
  container.register(TableSearchVectorSchemaMaintenanceProjection,
                    TableSearchVectorSchemaMaintenanceProjection, { lifecycle });
}
```

**Flow:** import package → @ProjectionHandler self-registers handlers into the event bus → registerV2TableOps fills ONLY the gaps (real adapters registered earlier win) → runners (`startTableQueryOpsAnalyzerIfEnabled`, `startTableQueryOpsTaskWorkerIfEnabled`) resolve config, return `undefined` when disabled, else fire once immediately then setInterval, returning `{stop}` handles.
**Invariant:** Disabled-by-default means the interval never starts — but the PROJECTION still registers so field events always have a scheduler to call (the Noop swallows them). Runners resolve logger and lease repository OPTIONALLY (`isRegistered ? resolve : undefined`) — missing infra degrades to silent operation, not crash.
**Probe:** `di.spec.ts:11` "registers the search-vector maintenance projection without a postgres adapter"; :31 "keeps an already-registered postgres scheduler".
**Coverage caveat:** runner loop internals (runners.ts) have no direct spec at this HEAD; wiring contract pinned by di.spec.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "registerV2TableOps v2TableOpsTokens startTableQueryOpsAnalyzerIfEnabled", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt isRegistered-gated defaults + class-token projection wiring (the comment-documented trap is real: decorator side-effects fire at import time); adapt token names; omit the specific config numbers.
