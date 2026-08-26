<!-- capsule-v2 -->
# Formula text-cast + gb_eq groupby rewrite — how do empty-string comparisons and grouped lookups avoid type-mismatch SQL?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does conditionV2 make `= ''`-style comparisons type-safe against formula output, and how do `gb_eq`/`gb_null` rewrite into lookup-aware comparisons?

## Dialect text casts + groupby op folding
**Path/Symbol:** `packages/nocodb/src/db/conditionV2.ts:formulaToTextCast` (:65-84), `oracleNarrowFormulaClobForCompare` (:96-109), gb_eq/gb_null branch (:249-296), blank/notblank formula arms (:779-855).
**Signature:** `formulaToTextCast(knex, expr)` → pg `(?)::text`, mysql `CAST((?) AS CHAR)`, mssql `CAST((?) AS NVARCHAR(MAX))` (T-SQL has NO valid `AS TEXT` target — `text` is the deprecated legacy type), oracle `CAST((?) AS VARCHAR2(4000))`, default `CAST((?) AS TEXT)`. `oracleNarrowFormulaClobForCompare(knex, column, expr)` → `DBMS_LOB.SUBSTR((?), 4000, 1)` ONLY for STRING-datatype formulas.
**Data Shape:** `gb_eq`/`gb_null` arrive as comparison_op values; the branch sets `filter.groupby = true` then either builds a lookup-subquery comparison or FOLDS the op down to plain `eq`/`blank`.

### Decisive source
```ts
// :60-64 — WHY the cast exists (verbatim): JSON_EXTRACT returns jsonb on PG
// and JSON on MySQL; a bare `<> ''` errors with a type mismatch. SQLite is
// already typeless-text (cast is a no-op). See nocodb/nocodb#12695.

// :267-286 — lookup/LTAR under gb_eq compares against the AGGREGATED value:
// eq binds the literal and hands the whole lookup builder as subquery;
// gb_null wraps it in parens for whereNull. Note rootApply: undefined.
if (column.uidt === UITypes.Lookup || column.uidt === UITypes.LinkToAnotherRecord) {
  const lkQb = await generateLookupSelectQuery({ baseModelSqlv2, alias, model,
    column, getAlias: getAliasGenerator('__gb_filter_lk') });
  return { rootApply: undefined,
    clause: (qb) => {
      if ((filter.comparison_op as any) === 'gb_eq')
        qb.where(knex.raw('?', [filter.value]) as any, lkQb.builder);
      else qb.whereNull(knex.raw(lkQb.builder).wrap('(', ')') as any);
    } };
}
// :287-295 — non-virtual columns fold: gb_eq ⇒ 'eq', gb_null ⇒ 'blank';
// QrCode/Barcode swap fk_column_id to their underlying VALUE column first
filter.comparison_op = (filter.comparison_op as any) === 'gb_eq' ? 'eq' : 'blank';
if ([UITypes.QrCode, UITypes.Barcode].includes(column.uidt))
  filter.fk_column_id = await column.getColOptions<BarcodeColumn|QrCodeColumn>(context)
    .then(col => col.fk_column_id);
```

**Flow:** leaf filter with gb_* op → resolve ref column (missing ⇒ fieldNotFound when throwErrorIfInvalid else silent skip) → virtual Lookup/LTAR? generate the aggregated-lookup subquery and compare literal-eq or IS NULL against it → otherwise fold to eq/blank (+ QR/barcode unwrap) and re-enter the normal ladder — where blank/notblank then apply the STRING-formula text cast so the empty-string arm is type-safe (`formulaToTextCast`) and Oracle skips both cast arms entirely (''≡NULL makes them unreachable).
**Invariant:** (1) The cast applies ONLY to formulas whose parsed_tree dataType is STRING — numeric rollups/formulas pass untouched (wrongly casting would break numeric comparisons). (2) gb_null on a NON-lookup column becomes `blank` (IS NULL **or** ''), but on a lookup it stays pure IS NULL against the aggregated string — the two are NOT interchangeable. (3) The groupby branch returns early with `rootApply: undefined`; nothing downstream may assume rootApply exists.
**Probe:** No unit tests upstream. Deterministic probe: gb_eq on an LTAR renders `? = (SELECT …json_agg…)`; gb_eq on SingleSelect renders plain `= ''` after fold; blank on STRING-formula renders `(… IS NULL OR CAST(expr AS …) = '')`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "formulaToTextCast gb_eq gb_null", limit: 5 });
// nocodb.packages.nocodb.src.db.conditionV2.parseConditionV2 Function conditionV2.ts 145-886
```

## Verdict
Adopt the four-way text-cast table (esp. MSSQL NVARCHAR(MAX) not TEXT), the CLOB-narrow-for-compare gate, and the gb_eq/gb_null fold-vs-subquery fork with QR/barcode unwrapping. Caveat: no direct tests at pin; graph ranges verified live.
