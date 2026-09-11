<!-- capsule-v2 -->
# pg-multivalue-scalar-aggregators — How does `UPPER({multiLookup})`-style scalar functions over multi-value fields become a per-element STRING_AGG?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** What is the dispatch that converts 22 formula functions into element-wise aggregators on PG?

## tryBuildMultiValueAggregator intercepts before the normal function table
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/sql-conversion.visitor.ts:tryBuildMultiValueAggregator` (:984-1086) + builders (:1264-1410).
**Signature:** `private tryBuildMultiValueAggregator(fnName, params, exprContexts): string | null` — null = fall through to the ordinary single-value translation.
**Data Shape:** gate: first param must be a multi-value expression AND driver === Pg. Builders: `buildPgNumericAggregator` (value/abs), `buildPgDatetimeFormatAggregator`, `buildPgDatetimeScalarAggregator` (datestr/timestr/day/month/year/weekday/weekNum/hour/minute/second/fromNow/toNow), `buildPgNumericScalarAggregator` (round/roundUp/roundDown/floor/ceiling/int) — 22 intercepted cases total.

### Decisive source
```ts
const isMulti = this.isMultiValueExpr(exprContexts[0], params[0]);
if (!isMulti) return null;
switch (fnName) {
  case FunctionName.DatetimeFormat:
    return this.buildPgDatetimeFormatAggregator(params[0], formatExpr);
  case FunctionName.Value:
    return this.buildPgNumericAggregator(params[0], (scalarText) => this.formulaQuery.value(scalarText));
  ...
}
// every builder shares the skeleton:
const normalizedJson = this.normalizeMultiValueExprToJson(valueExpr);   // pg_typeof-guarded coercion to jsonb array
const aggregated = this.dialect!.stringAggregate(safeExpr, ', ', 'ord');
return `(CASE WHEN ${normalizedJson} IS NULL THEN NULL
  ELSE (SELECT ${aggregated} FROM jsonb_array_elements(${normalizedJson}) WITH ORDINALITY AS t(elem, ord)) END)`;
```

**Flow:** function call → multiplicity normalization of params (`normalizeFunctionParamsForMultiplicity` reduces non-aggregate multi params to their FIRST scalar via the jsonb extractor, unless the fn accepts multi or this interceptor will handle it) → aggregator probe → per-element scalar SQL built by re-invoking the SAME formulaQuery method on the extracted scalar text → string_agg with ordinality order.
**Invariant:** the interceptor must run BEFORE the plain dispatch (it does — inside `execute()`), and element extraction uses `WITH ORDINALITY ... ORDER BY ord` so element order survives aggregation. The pg_typeof CASE ladder (json/json/text/array-wrap) tolerates any stored shape.
**Probe:** static byte-exact: `grep -c 'return this.buildPgDatetimeScalarAggregator\|return this.buildPgNumericScalarAggregator\|return this.buildPgNumericAggregator\|return this.buildPgDatetimeFormatAggregator' sql-conversion.visitor.ts` → 22.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"tryBuildMultiValueAggregator","limit":3,"detail":"ids"}'
```

## Verdict
Adopt the interceptor-before-dispatch structure and the shared aggregate skeleton. Adapt the function set. Omit nothing else.
