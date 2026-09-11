<!-- capsule-v2 -->
# rollup-function-support-matrix — What are the exact SQL shapes per rollup function on PG (and the deliberate SUM(0) stub)?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does the dialect compile sum/average/count/countall/max/min/and/or/xor/array_join/array_unique/array_compact over link CTE values?

## rollupAggregate switch keyed on fn + target-field type; non-numeric targets get SUM(0)/AVG(0)
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/providers/pg-record-query-dialect.ts:rollupAggregate` (:464-589) + single-value twin `singleValueRollupAggregate` (:590-647).
**Signature:** `rollupAggregate(fn, fieldExpression, opts: { targetField?, orderByField?, rowPresenceExpr?, flattenNestedArray? }): string`.
**Data Shape:** everything numeric casts through `CAST(… AS DOUBLE PRECISION)` (`castAgg`); countall over MultipleSelect counts jsonb elements; xor = parity of true count.

### Decisive source
```ts
case 'sum':
  if (isNumericTarget) {
    if (targetField?.isMultipleCellValue) return this.castAgg(`COALESCE(SUM(${this.buildJsonNumericSumExpression(fieldExpression)}), 0)`);
    return this.castAgg(`COALESCE(SUM(${fieldExpression}), 0)`);
  }
  return this.castAgg('SUM(0)');        // never cast a non-numeric column
...
case 'countall': {
  if (targetField?.type === FieldType.MultipleSelect) {
    return this.castAgg(`COALESCE(SUM(CASE WHEN ${f} IS NOT NULL THEN jsonb_array_length(${f}::jsonb) ELSE 0 END), 0)`);
  }
  const base = rowPresenceExpr ?? fieldExpression;
  return this.castAgg(`COALESCE(COUNT(${base}), 0)`);
}
```
array_unique/array_compact with `flattenNestedArray` build a recursive flattener (`WITH RECURSIVE flattened(val) … CROSS JOIN LATERAL jsonb_array_elements`) or the shared `buildDistinctFlattenedJsonArray` (DISTINCT + sorted jsonb_agg).

**Flow:** fn + target classification → multi-value targets expand to per-element CASE sums/counts → ordering functions take STRING_AGG/jsonb_agg ORDER BY variants → unknown fn THROWS (`Unsupported rollup function`).
**Invariant:** SUM/AVG on a non-numeric target deliberately emit constant aggregates instead of casting — silent zero beats a query-breaking type error, and UI-level validation is expected to prevent configuring such rollups. Single-value relationships bypass aggregation entirely via the twin (count→0/1, sum→COALESCE CAST of itself).
**Probe:** static byte-exact: `grep -n "SUM(0)\|AVG(0)" providers/pg-record-query-dialect.ts` → :491/:505; `grep -c 'jsonb_array_elements' providers/pg-record-query-dialect.ts`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"rollupAggregate","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the matrix incl. stubs and recursive flatteners. Adapt cast types. Omit nothing.
