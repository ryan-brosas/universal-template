<!-- capsule-v2 -->
# conditional-aggregate-cast-envelope — What cast/unwrap envelope wraps every conditional aggregate before it enters a CTE column?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does an array_join or json_agg result become the rollup field's declared dbFieldType safely?

## unwrapJsonAggregateForScalar → castExpressionForDbType, with array-function formatted-input special case
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:castExpressionForDbType` (:960-996) + envelope application (:1374-1390 equality plan; :1554-1568 fallback; :1806-1830 lookup).
**Signature:** `private castExpressionForDbType(expression: string, field: FieldCore): string` — suffix map Json::jsonb / Integer / Real double precision / DateTime timestamptz / Boolean / Blob bytea / Text.
**Data Shape:** input selection: `useFormattedForArrayFunctions` = (target ∈ {Link, Formula, ConditionalRollup}) AND fn ∈ {array_join, concatenate, array_unique, array_compact} — those read the FORMATTED display expression, all others read RAW physical values.

### Decisive source
```ts
const aggregatesToJson = JSON_AGG_FUNCTIONS.has(aggregationFn);
const normalizedAggregateExpression = unwrapJsonAggregateForScalar(
  this.dbProvider.driver,
  aggregateExpression,
  field,
  aggregatesToJson
);
const castedAggregateExpression = this.castExpressionForDbType(normalizedAggregateExpression, field);
...
countsQuery.select(this.qb.client.raw(`${castedAggregateExpression} as "reference_value"`));
```

**Flow:** build raw aggregation SQL for the chosen fn (+ORDER BY when ordering fns) → unwrap json aggregates to scalar when the FIELD's type is scalar → wrap in `(expr)::type` per declared dbFieldType → emitted as reference_value inside counts/aggregates subqueries and as `conditional_rollup_<id>` in CTE columns.
**Invariant:** the cast targets the ROLLUP FIELD's stored column type, not the target field's — a countall over links lands as integer even though titles are text. Skipping the envelope yields `UPDATE ... FROM` assignment errors (the exact class pass-10's write plane documented), because PG will not implicitly coerce jsonb→text columns on UPDATE.
**Probe:** static byte-exact: `grep -n 'castedAggregateExpression' field-cte-visitor.ts | head -3`; upstream spec pins sibling IF-side casts (`generated-column-query.postgres.spec.ts` expects `double precision`).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"castExpressionForDbType","limit":5,"detail":"ids"}'
```

## Verdict
Adopt unwrap-then-cast keyed to the consuming column. Adapt suffix map. Omit nothing.
