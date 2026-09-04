<!-- capsule-v2 -->
# Table/view operation plugin runners — why do guard plugins run twice, once outside and once inside the transaction?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do table-level and view-level operation plugins differ from the record/field runners — specifically, when does `guard` execute relative to the DB transaction?

## TableOperationPluginRunner / ViewOperationPluginRunner
**Path/Symbol:** `packages/v2/core/src/application/services/TableOperationPluginRunner.ts` — shared `createEnforceGroups` (:19–33), `withTransactionBoundContext` (:35–45), `TableOperationPluginExecution.guard(executionContext?)` (:47–77), runner `prepare` (:127–150); twin `ViewOperationPluginRunner.ts` :51–160 (same shape, view kinds).
**Signature:** `runner.prepare(context): Promise<Result<Execution, DomainError>>`; `execution.guard(executionContext?: IExecutionContext): Promise<Result<void, DomainError>>`.
**Data Shape:** PreparedPluginEntry `{plugin, preparedState: unknown}`; enforce groups ordered pre(0) → default(1) → post(2).

### Decisive source
```ts
const withTransactionBoundContext = (
  context: TableOperationPluginContext,
  executionContext: IExecutionContext
): TableOperationPluginContext => ({
  ...context,
  executionContext,
  isTransactionBound: true,
} as TableOperationPluginContext);

// Execution.guard re-binds per call:
const context = executionContext
  ? withTransactionBoundContext(this.context, executionContext)
  : this.context;
```

**Flow:** prepare phase filters plugins by `supports(kind)` and runs `prepare()` group-parallel (pre→default→post), collecting preparedState — OUTSIDE any transaction; later, inside the operation's transaction, `guard(txContext)` re-runs ALL groups' `guard()` with a context flagged `isTransactionBound: true`, failing the operation on first errored result. Unlike FieldOperation/RecordWrite runners there are NO beforePersist/afterCommit hooks here — these runners are pure gatekeepers.
**Invariant:** The two-phase design exists because limit checks must see committed state at prepare time (cheap counts, no locks) but enforcement must be race-safe INSIDE the write transaction; a porter who runs guard only at prepare keeps the TOCTOU window open. Errors map to namespaced codes (`table_operation_plugin.guard_failed`) with `{operation, plugin}` details so one noisy plugin is attributable.
**Probe:** `packages/v2/core/src/application/services/TableDataSafetyLimitTableOperationPlugin.spec.ts` (:400 rejects create over fields-per-table limit, :418 counts existing tables without hydrating aggregates, :480 composes multiple limit plugins taking the strictest numeric limit); runner itself shares the createEnforceGroups core verified by field-runner spec.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableOperationPluginRunner withTransactionBoundContext createEnforceGroups", limit: 10 });
```

## Verdict
Adopt the prepare-outside/guard-inside split with explicit `isTransactionBound` context flag and strictest-limit composition for resource caps; adapt plugin kind unions and context shapes to host; omit the view twin if host has no view-scoped operations (it is a parameterization, not a new mechanism).
