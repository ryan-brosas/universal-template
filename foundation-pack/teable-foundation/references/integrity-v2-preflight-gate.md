<!-- capsule-v2 -->
# Hydration preflight gate — why does base integrity check COUNT fields before hydrating any table?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do you stream base-wide checks when some tables cannot be hydrated at all?

## inspectBaseTablesBeforeHydration + createBaseTableHydrationIssue
**Path/Symbol:** `apps/nestjs-backend/src/features/integrity/integrity-v2.service.ts:inspectBaseTablesBeforeHydration` (:362–406), `:createBaseTableHydrationIssue` (:407–457); wired in `resolveBaseTarget` :320–359.
**Signature:** `inspectBaseTablesBeforeHydration(metaDb, baseId): Promise<{tableIds: TableId[]; issues: IBaseTargetPreflightIssue[]}>`.
**Data Shape:** Single grouped SQL over meta tables; rows carry string/bigint counts (`activeFieldCount`, `primaryFieldCount`) normalized via `Number()`.

### Decisive source
```ts
.select([
  't.id as tableId', 't.name as tableName',
  sql<number>`count(${sql.ref('f.id')})`.as('activeFieldCount'),
  sql<number>`count(${sql.ref('f.id')}) filter (where ${sql.ref('f.is_primary')} = true)`.as('primaryFieldCount'),
])
...
if (activeFieldCount > 0 && primaryFieldCount === 0) {
  issues.push(this.createBaseTableHydrationIssue(...)); // ruleId table_missing_primary_field
}
```
```ts
// Physical schema integrity should not validate deleted tables or fields. The repository
// hydrates only fields/views with deleted_time IS NULL for activeWithPending.
const schemaIntegrityTableState: TableQueryState = 'activeWithPending';
```

**Flow:** One grouped meta-db query counts active and primary fields per table BEFORE any repository hydration → tables with ≥1 active field form the hydration spec (empty spec skipped entirely — `tableSpec` undefined → `ok([])`); zero-primary tables still hydrate BUT emit a non-repairable preflight issue (repair.available:false, mode:'manual') ahead of the stream. Preflight issues yield FIRST in `streamBaseChecks` (:663–697) so consumers see blockers before per-table noise.
**Invariant:** Hydration must exclude zero-active-field tables (V2 cannot build a Table without fields) yet must NOT silently drop them from reporting — the synthetic issue preserves visibility with `fieldId = tableId` placeholder and `'System Columns'` fieldName.
**Probe:** `grep -cF 'table_missing_primary_field' apps/nestjs-backend/src/features/integrity/integrity-v2.service.ts` → 1; direct tests `integrity-v2.service.spec.ts` :496 ('keeps active tables with no fields out of V2 hydration'), :548 ('reports active tables without a primary field while still hydrating them').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "inspectBaseTablesBeforeHydration primaryFieldCount preflight", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt count-before-hydrate preflight with manual-mode synthetic issues; adapt to your meta schema; omit the i18n-ready message scaffolding if unused.
