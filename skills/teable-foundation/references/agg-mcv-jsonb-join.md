<!-- capsule-v2 -->
# MCV jsonb-join aggregation — how are multi-cell-value aggregates computed without flattening in SQL?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do SUM/AVG/MIN/MAX work over a jsonb array cell (lookup/link/multi-select) where one ROW holds N values?

## CTE-per-field + cross-join MAX wrapper
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/aggregation-query/aggregation-function.abstract.ts:compiler` (:67–92) — the `ignoreMcvFunc` list and the `${fieldId}_mcv` join; adapters in `postgres/single-value/single-value-aggregation.adapter.ts` and `postgres/multiple-value/multiple-value-aggregation.adapter.ts`.
**Signature:** `compiler(builder, aggFunc, alias)`; branch on `field.isMultipleCellValue && !ignoreMcvFunc.includes(aggFunc)`.
**Data Shape:** MCV cells are jsonb arrays; the per-row subquery yields ONE scalar column named `"value"`.

### Decisive source
```ts
if (isMultipleCellValue && !ignoreMcvFunc.includes(aggFunc)) {
  const joinTable = `${fieldId}_mcv`;
  builderClient.with(`${fieldId}_mcv`, this.knex.raw(rawSql));
  builderClient.joinRaw(`, ${this.knex.ref(joinTable)}`);
  rawSql = `MAX(${this.knex.ref(`${joinTable}.value`)})`;
}
```

**Flow:** For an MCV field + non-exempt func: the adapter's raw SQL is itself a complete single-row query (`SELECT SUM(...) AS "value" FROM <table> t, jsonb_array_elements_text(cell::jsonb)`) → registered as a CTE named `<fieldId>_mcv` → cross-joined into the outer aggregate via `, mcv` in FROM → the outer select takes `MAX(mcv.value)` to collapse the single row back to a scalar. Exempt funcs (COUNT/Empty/Filled/Checked/UnChecked/PercentEmpty/PercentFilled/PercentChecked/PercentUnChecked/TotalAttachmentSize) operate per-row directly and skip the join entirely.
**Invariant:** The exemption list is semantic, not arbitrary — presence/count-class aggregates must count ROWS not elements, so they read the raw cell; value-class aggregates need element-level iteration. Porters who flatten first break percent-filled semantics (a 3-element array is still ONE filled row). The CTE name embeds fieldId because multiple MCV fields can be aggregated in one query — collisions would cross-join the wrong subquery.
**Probe:** `grep -cF 'joinRaw' apps/nestjs-backend/src/db-provider/aggregation-query/aggregation-function.abstract.ts` → 1; `grep -cF 'jsonb_array_elements_text' apps/nestjs-backend/src/db-provider/aggregation-query/postgres/multiple-value/multiple-value-aggregation.adapter.ts` → 8.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "MultipleValueAggregationAdapter jsonb_array_elements_text ignoreMcvFunc", limit: 10 });
```

## Verdict
Adopt CTE-per-mcv-field + cross-join collapse when your storage keeps arrays as jsonb; adapt names to your alias discipline; omit for scalar-only columns.
