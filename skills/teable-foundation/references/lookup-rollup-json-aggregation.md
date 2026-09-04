<!-- capsule-v2 -->
# Lookup/rollup JSONB aggregation semantics — nested-array flattening, FILTER-NULL aggregation, and hostile-text numeric coercion

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do lookup-of-lookup chains and rollups over messy text stay v1-compatible: when do arrays flatten one level vs recursively, and how are non-numeric strings coerced inside SUM/AVG without aborting the query?

## Single-level vs recursive flattening + sanitize-then-coerce numerics
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/ComputedTableRecordQueryBuilder.ts` — `buildLookupAggExpr` (:2437–2515): jsonb-storage detection via `dbFieldType === 'JSON'` OR user/system snapshot sources :2464–2470; single-level flatten `canUseSingleLevelLookupFlatten` (:2388–2397: plain lookup WITHOUT filter) + `buildSingleLevelLookupFlattenExpr` (:2404–2420); recursive `WITH RECURSIVE __flat` fallback :2477–2490 with v1-compat doc comment :2422–2436 ("to_jsonb: [\"[10]\"] WRONG / ::jsonb: [[10]] nested / flatten: [10] correct"); rollup expression switch `buildRollupAggregateExpr` (:2517–2684) incl. multi-value numeric paths and per-type aggregates (`countall` multipleSelect → `jsonb_array_length` sum :2576–2585; xor = odd count of trues :2609–2612; array_unique/array_compact nested flattening :2637–2678); numeric sanitizer `sanitizeNumericTextExpression` (:2686–2710: strip `[,\\s]`, regex prefix match, exponent rejection gated by `typeValidationStrategy.isValidForType`), `buildJsonNumericSumExpression`/`CountExpression` (:2712–2745), `castAgg` DOUBLE PRECISION :2747–2749.
**Signature:** `buildLookupAggExpr(foreignTable, foreignFieldId, outputAlias, {tableAlias?, orderBy?, isMultiValue?})`; `buildRollupAggregateExpr(foreignTable, foreignFieldId, expression: RollupFunction, {tableAlias?, orderBy?, filterWhere?})`.
**Data Shape:** lookups aggregate `jsonb_agg(expr ORDER BY …) FILTER (WHERE expr IS NOT NULL)`; date-time targets serialize as UTC `to_char(...'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"')` before to_jsonb (:2504–2506); single-value outputs use `-> 0`.

### Decisive source
```ts
if (isJsonbStorage) {
  const aggExpr = sql`jsonb_agg(${colRef}::jsonb${orderByRef}) FILTER (WHERE ${colRef} IS NOT NULL)`;
  const flattenedExpr = this.canUseSingleLevelLookupFlatten(foreignField)
    ? this.buildSingleLevelLookupFlattenExpr(aggExpr)      // one level, order-preserving
    : sql`( WITH RECURSIVE __flat(e) AS (
        SELECT ${aggExpr} UNION ALL
        SELECT jsonb_array_elements(CASE WHEN jsonb_typeof(__flat.e)='array' THEN __flat.e ELSE '[]'::jsonb END)
        FROM __flat )
      SELECT jsonb_agg(e) FILTER (WHERE jsonb_typeof(e) <> 'array') FROM __flat )`;
  return ok(isMultiValue ? flattenedExpr.as(outputAlias) : sql`${flattenedExpr} -> 0`.as(outputAlias));
}
```
```ts
// Numeric coercion for SUM/AVG over text-stored values:
const normalized = sql`NULLIF(REGEXP_REPLACE(BTRIM((${expr})::text), '[,\s]', '', 'g'), '')`;
-- prefix-match a plain decimal, REJECT exponents, validate via type strategy, else NULL
WHEN __num_prefix IS NOT NULL AND NOT has_exponent AND ${isValidNumeric} THEN (__num_prefix)::double precision
ELSE NULL
// array cells: SUM over jsonb_array_elements_text of the sanitized scalars; NULL→0 wrappers everywhere
```
**Flow:** lookup aggregation first asks whether the source column actually stores JSONB (dbFieldType or system snapshot) — TEXT columns never take the flatten path → filtered jsonb_agg preserves row order via explicit tie-breakers → nesting decides flattening depth: an unfiltered plain lookup reading another lookup's already-flat array needs exactly ONE level; anything else (filters, deeper chains) takes the recursive path so `[["a"],"b"]` becomes `["a","b"]`, never `["[10]"]` string-encoding → rollups branch per expression AND per cell value type/multiplicity, coercing dirty text through strip→prefix→validate→NULL rather than throwing.
**Invariant:** aggregation NEVER errors on malformed cell text — it degrades that element to NULL/0 while keeping the rest of the aggregate; flattening must preserve outer-row then inner-element order (ORDINALITY columns) because clients compare arrays positionally; single-value extraction uses jsonb subscripting only.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/computed/ComputedTableRecordQueryBuilder.spec.ts` — `"uses single-level flattening for lookup-of-lookup chains without inner filters"` (:1612), `"keeps recursive flattening for lookup-of-lookup chains with filtered inner lookups"` (:1633), `"rollup snapshot for <expression>"` loops (:2121/:2138), `"rollup array_unique flattens multi-value field entries before deduplication"` (:2205).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildLookupAggExpr buildRollupAggregateExpr", limit: 5 });
// → both methods …/query-builder/computed/ComputedTableRecordQueryBuilder.ts 2437-2515 / 2517-2684
```

## Verdict
Adopt the storage-aware branching (JSONB vs text), the one-level-vs-recursive flatten rule keyed on "plain unfiltered lookup", and the sanitize-then-coerce numeric ladder with exponent rejection — each encodes a real upstream data-shape bug (string-encoded arrays, comma-formatted numbers). Adapt regex/limits to your locale rules. Omit teable's exact UTC format if your wire format differs. Coverage caveat: none material at this pin.
