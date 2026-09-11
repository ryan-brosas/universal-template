<!-- capsule-v2 -->
# Statistic-func validity table — per-cell-type allowed aggregates with user/link/attachment deltas

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Which statistic functions are legal for which field, and where is that decided?

## getValidStatisticFunc switch + post-switch pullAll/push
**Path/Symbol:** `packages/core/src/models/aggregation/statistic.ts:getValidStatisticFunc` (:5–105); direct spec `statistic.spec.ts` (8 cases incl. attachment :133–147); consumers: `aggregation-open-api.service.ts:validFieldStats` (:98–126) and `aggregation-query.abstract.ts:validAggregationField` (:90–110).
**Signature:** `getValidStatisticFunc(field?: {type, cellValueType, isMultipleCellValue?}): StatisticsFunc[]`.
**Data Shape:** ordered enum arrays; ORDER matters (UI renders in this order; the user-family branch SPLICES at index 3).

### Decisive source
```ts
if ([FieldType.User, FieldType.CreatedBy, FieldType.LastModifiedBy].includes(type)) {
  statisticSet = [Count, Empty, Filled, PercentEmpty, PercentFilled];
  if (!isMultipleCellValue) {
    statisticSet.splice(3, 0, StatisticsFunc.Unique);      // insert mid-array
    statisticSet.push(StatisticsFunc.PercentUnique);
  }
  return statisticSet;
}
...
if (type === FieldType.Attachment) {
  pullAll(statisticSet, [StatisticsFunc.Unique, StatisticsFunc.PercentUnique]);
  statisticSet.push(StatisticsFunc.TotalAttachmentSize);
}
```

**Flow:** Link fields short-circuit to count/presence family. User family gets Unique/PercentUnique ONLY when single-valued (spliced mid-list so UI order stays Count, Empty, Filled, Unique, Percent*). Cell-value switch covers String (text family), Number (+Sum/Average/Min/Max), DateTime (+Earliest/Latest/DateRangeOfDays/Months), Boolean (checked family). Attachment then REMOVES uniqueness and APPENDS TotalAttachmentSize regardless of cell type.
**Invariant:** The array order IS a UI contract (spec pins exact sequences) — porters who sort or rebuild these lists change menu ordering for every client. The attachment post-pass proves validity is TYPE-over-CELLTYPE composable: attachment cells are String-typed yet lose Unique because "unique attachment" is meaningless while sizes are summable. Multi-value user cells drop Uniques because element-level distinct contradicts the row-based MCV aggregation actually computed.
**Probe:** `grep -cF 'splice(3, 0, StatisticsFunc.Unique)' packages/core/src/models/aggregation/statistic.ts` → 1; `grep -cF 'TotalAttachmentSize' apps/nestjs-backend/src/db-provider/aggregation-query/aggregation-function.abstract.ts` → 2.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getValidStatisticFunc TotalAttachmentSize splice", limit: 10 });
```

## Verdict
Adopt a single pure validity function consumed by BOTH api-validation and SQL layers; adapt the matrix to your field taxonomy; keep list order stable once clients depend on it.
