<!-- capsule-v2 -->
# Symbol-token service indirection — AGGREGATION_SERVICE_SYMBOL provider seam

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does the aggregation module let consumers inject a service implementation without importing its class (and why)?

## Symbol token + provider + decorator trio
**Path/Symbol:** token `apps/nestjs-backend/src/features/aggregation/aggregation.service.symbol.ts` (:6); decorator `aggregation.service.provider.ts:InjectAggregationService` (:16); registration `aggregation.module.ts` (:17–21, exports :23); barrel re-exports `index.ts` (:1–9).
**Signature:** `AGGREGATION_SERVICE_SYMBOL = Symbol('AGGREGATION_SERVICE')`; `InjectAggregationService() = Inject(AGGREGATION_SERVICE_SYMBOL)`.
**Data Shape:** module providers bind BOTH the class AND the symbol to AggregationService; consumers type against `IAggregationService`.

### Decisive source
```ts
{
  provide: AGGREGATION_SERVICE_SYMBOL,
  useClass: AggregationService,
},
...
exports: [AGGREGATION_SERVICE_SYMBOL, AggregationService],
```

**Flow:** Consumers (`AggregationOpenApiService` :28) inject via the decorator and program against the interface — the concrete class stays an internal of AggregationModule. The open-api spec mirrors the dual binding (:19–22) so tests can swap implementations under the same token.
**Invariant:** This is teable's v1-side echo of the v2 hexagonal di-tokens discipline (pack's `di-tokens` capsule): import-direction hygiene is enforced by making the TOKEN the public surface — a porter who injects the class directly couples their module graph to implementation and loses the swap point. The duplicated `useClass` line at :20 is a vestige comment, not a second binding. Both exports are needed because legacy callers (record.service etc.) still take the concrete type.
**Probe:** `grep -cF "Symbol('AGGREGATION_SERVICE')" apps/nestjs-backend/src/features/aggregation/aggregation.service.symbol.ts` → 1; `grep -cF 'Inject(AGGREGATION_SERVICE_SYMBOL)' apps/nestjs-backend/src/features/aggregation/aggregation.service.provider.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "AGGREGATION_SERVICE_SYMBOL InjectAggregationService", limit: 10 });
```

## Verdict
Adopt symbol-token + interface injection for service seams you expect to fork per-edition; adapt naming; omit when your DI already keys by interface.
