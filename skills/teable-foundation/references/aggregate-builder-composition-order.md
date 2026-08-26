<!-- capsule-v2 -->
# aggregate-builder-composition-order — In what order are aggregation, grouping, and group ordering appended to a shared knex builder?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the append sequence in createRecordAggregateBuilder and why does groupBy deliberately bypass the aggregation compiler?

## filter → aggregationQuery.appendBuilder → (optional) groupQuery.appendGroupBuilder → per-group orderAggregateByGroup
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:createRecordAggregateBuilder` (:228-306).
**Signature:** composition over ONE qb threaded through dbProvider sub-builders; `fieldMap` built id→FieldCore for the whole table.
**Data Shape:** aggregationQuery receives `groupBy: undefined` explicitly with a comment; GroupQuery handles grouping; each group item then appends its own ORDER BY expression.

### Decisive source
```ts
// Apply aggregation (do NOT pass groupBy here; grouping is handled by GroupQuery below)
this.dbProvider.aggregationQuery(qb, fieldMap, aggregationFields, undefined, {
  selectionMap, tableDbName: table.dbTableName, tableAlias: alias,
}).appendBuilder();

if (groupBy && groupBy.length > 0) {
  this.dbProvider.groupQuery(qb, fieldMap, groupByFieldIds, undefined, { selectionMap }).appendGroupBuilder();
  for (const groupItem of groupBy) {
    ...
    this.orderAggregateByGroup(qb, groupedField, direction, selectionMap);
  }
}
```

**Flow:** BASE/CTE construction upstream → aggregate SELECT expressions aliased per `<fieldId>_<func>` → filter compiled against the same selectionMap → aggregation appended → grouping appended → choice-aware ORDER BYs appended last.
**Invariant:** separation of concerns is load-bearing: the aggregation compiler must stay group-blind (its SQL assumes row scope), while GroupQuery owns GROUP BY emission — merging them duplicates alias logic. Filter-before-aggregate ordering means aggregates see filtered rows.
**Probe:** upstream direct spec `record-query-builder-group-quoting.spec.ts` drives this exact composition (aggregationFields + groupBy through createRecordAggregateBuilder) asserting quoted qualified group columns.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"appendGroupBuilder","limit":5,"detail":"ids"}'
```

## Verdict
Adopt the append order + group-blind aggregation rule. Adapt builder API. Omit nothing.
