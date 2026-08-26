<!-- capsule-v2 -->
# Persisted-computed backfill re-entry — how do you rebuild computed columns through the normal pipeline instead of a bespoke bulk path?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does maintenance code trigger full-table computed recomputes safely?

## PersistedComputedBackfillService.recomputeForTables
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/persisted-computed-backfill.service.ts:PersistedComputedBackfillService.recomputeForTables` (:117–180).
**Signature:** `recomputeForTables(tableIds: string[]): Promise<void>`.

### Decisive source
```ts
async recomputeForTables(tableIds: string[]) {
  if (!this.cls.isActive()) {
    return this.cls.run(() => this.recomputeForTablesInContext(tableIds));   // :126–128
  }
  ...
  await this.computedOrchestrator.computeCellChangesForFieldsAfterCreate(sources, async () => {
    return;                                                                  // :176–178 no-op update
  });
```

**Flow:** CLS context self-heal (wraps itself if called outside any request scope) → query surviving fields per table → keep only persisted-computed classes (Formula/Rollup/ConditionalRollup by type-set membership OR isComputed flag) plus link-display and lookup fields (:146–165) → call the CREATE-field orchestrator path with a NO-OP update callback. That path already does post-update collection, preferAutoNumberPaging=true, publish-target exclusion (:orchestrator :317–357).
**Invariant:** Reuse-over-special-case: no second bulk writer exists; backfill rides field-creation semantics so locking/paging/publishing stay identical to product paths. The CLS guard makes the service callable from cron/maintenance outside HTTP request context.
**Probe:** needle verified at this pin (`cls.isActive()` :126, no-op callback :176); graph retrieval `PersistedComputedBackfillService` resolves :117–180.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "PersistedComputedBackfillService", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pipeline-reuse + CLS self-wrap; adapt field-class filter to your schema; omit NestJS CLS if your DI has ambient context already.
