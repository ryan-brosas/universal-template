<!-- capsule-v2 -->
# Schema-change maintenance projection — how do field events trigger search-index upkeep without blocking the event handler?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does an event projection convert FieldCreated/Updated/Deleted into scheduler work while guaranteeing handler success regardless of scheduling failure?

## Warn-don't-fail projection + reason vocabulary
**Path/Symbol:** `packages/v2/table-query-ops/src/searchVectorSchemaMaintenance.ts` whole (70L): `TableSearchVectorSchemaMaintenanceProjection` (:28-62), `@ProjectionHandler(FieldCreated|FieldUpdated|FieldDeleted)` (:24-26), `maintenanceReason` (:64-70).
**Signature:** `handle(context, event) → Promise<Result<undefined, DomainError>>` — ALWAYS resolves ok.
**Data Shape:** schedule input `{table (rehydrated aggregate), reason: 'field_created'|'field_updated'|'field_deleted'}`; result `{status: 'queued'|'coalesced'} | undefined`.

### Decisive source
```ts
const scheduled = await safeTry(async function* () {
  const spec  = yield* Table.specs(event.baseId).byId(event.tableId).build().safeUnwrap();
  const table = yield* (await tableRepository.findOne(context, spec)).safeUnwrap();
  yield* (await scheduler.schedule(context, { table, reason: maintenanceReason(event) })).safeUnwrap();
  return ok(undefined);
});
if (scheduled.isErr()) {
  this.logger.warn('Failed to schedule search vector maintenance after field schema change', {
    tableId: event.tableId.toString(), fieldId: event.fieldId.toString(), error: scheduled.error.message });
}
return ok(undefined);   // the projection NEVER propagates the scheduling error
```

**Flow:** field event → rehydrate Table aggregate via spec → map event class to reason → scheduler.schedule (the postgres adapter coalesces per-table under an advisory xact lock; Noop swallows when adapters are off — see query-ops-di-noop-wiring) → any failure logged at WARN with table+field ids, handler still returns ok so the event bus records delivery success.
**Invariant:** Maintenance is best-effort BY DESIGN: a failed schedule must not fail the originating field mutation (which already committed); the next schema change or explicit rebuild heals staleness (status reader reports `stale`). Reason is carried so coalescing can UPGRADE the pending task's reason rather than enqueue duplicates.
**Probe:** `searchVectorSchemaMaintenance.spec.ts` — two direct specs (projection wiring incl. "registers … without a postgres adapter" twin in di.spec.ts:11).
**Coverage caveat:** scheduling-failure logging path itself untested upstream; behavior verified by source reading.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableSearchVectorSchemaMaintenanceProjection ProjectionHandler maintenanceReason", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt warn-don't-fail projections for derived-maintenance triggers; adapt the reason enum; keep the rehydrate-then-schedule shape so schedulers receive aggregates, not raw rows.
