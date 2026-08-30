<!-- capsule-v2 -->
# Aggregation SQL compiler ladder — how does one request compile into per-field aggregate SQL?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How does a statistics request (field + func list) become concrete aggregate SELECT expressions, and where is func-validity enforced?

## createRecordAggregateBuilder → aggregationQuery → compiler
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:createRecordAggregateBuilder` (:228–307); `apps/nestjs-backend/src/db-provider/postgres.provider.ts:aggregationQuery` (:545–560) instantiating `AggregationQueryPostgres`; dispatch in `apps/nestjs-backend/src/db-provider/aggregation-query/aggregation-query.abstract.ts:appendBuilder` (:29–88) and `compiler` map (`aggregation-function.abstract.ts:38–97`).
**Signature:** `createRecordAggregateBuilder(from, options): Promise<{qb, alias, selectionMap}>`; per field `compiler(qb, aggFunc, alias?)`.
**Data Shape:** `IAggregationField = {fieldId, statisticFunc?, alias?}`; alias defaults to `` `${fieldId}_${aggFunc}` `` (:95) — the exact string the service later reads results by.

### Decisive source
```ts
// aggregation-query.abstract.ts — validity gate BEFORE any SQL
const validStatisticFunc = getValidStatisticFunc(field);
if (statisticFunc && !validStatisticFunc.includes(statisticFunc)) {
  throw new BadRequestException(`field: '${fieldId}', aggregation func: '${statisticFunc}' is invalid, ...`);
}
// aggregation-function.abstract.ts — handler map + select emission
let rawSql: string = chosenHandler();
...
return builderClient.select(this.knex.raw(`${rawSql} AS ??`, [alias ?? `${fieldId}_${aggFunc}`]));
```

**Flow:** Builder creates the base query (view CTE / BASE pagination CTE) → `buildAggregateSelect` registers per-field selection expressions → filter applied with an AUGMENTED selectionMap (every table field qualified `${alias}.${dbFieldName}` so hidden fields still filter, :716–751) → `aggregationQuery(...).appendBuilder()` validates each (fieldId, func), resolves the column ref from the selectionMap FIRST, then emits one raw `SELECT <sql> AS alias` per statistic. Grouping rides the separate `groupQuery().appendGroupBuilder()`, deliberately NOT through `extra.groupBy` here (:282 comment).
**Invariant:** Validity is enforced TWICE at independent layers — the open-api service pre-validates against `getValidStatisticFunc(fieldInstance)` for a clean 400, and the SQL layer re-throws BadRequest if a caller bypassed it; porters who keep only one layer break internal callers. The column reference MUST come from `selectionMap.get(id)` when present — falling back to bare dbFieldName under a permission CTE reads the wrong (unprojected) source.
**Probe:** `grep -cF 'getValidStatisticFunc' apps/nestjs-backend/src/db-provider/aggregation-query/aggregation-query.abstract.ts` → 1; `grep -cF 'AS ??' apps/nestjs-backend/src/db-provider/aggregation-query/aggregation-function.abstract.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "createRecordAggregateBuilder appendBuilder validAggregationField", limit: 10 });
```

## Verdict
Adopt the three-layer funnel (request validation → builder state → SQL emission) with alias-per-func result keys; adapt the validity table to your field model; omit the dual-DB router if single-database.
