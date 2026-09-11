<!-- capsule-v2 -->
# Rollup SQL compiler — how does a rollup become a correlated aggregate that survives boolean types, nested rollups, and MSSQL's no-agg-over-subquery rule?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What is the exact construction of `genRollupSelectv2`'s per-relation correlated subquery and its dialect corrections?

## Correlated rollup builder
**Path/Symbol:** `packages/nocodb/src/db/genRollupSelectv2.ts:genRollupSelectv2` (:32-565), inner `applyFunction` (:149-370), `wrapMssqlNestedAgg` (:375-389).
**Signature:** `genRollupSelectv2({baseModelSqlv2, knex, alias?, columnOptions: RollupColumn|LinksColumn, parentColumns?: CircularRefContext, nestedLevel? = 0}): Promise<{builder}>` — callers `.as()` the builder (knex Raw lacks `.as()`, hence a QueryBuilder is REQUIRED; Oracle sentinel adds `.from(dual)` because Oracle rejects FROM-less SELECT).
**Data Shape:** Failure contract is an ERROR SENTINEL, never a throw: `SELECT 'ERR' [FROM dual]` when `columnOptions.error` / relation column missing / rollup column not aggregatable. Alias minting: `` `__nc_rollup_` + Math.random().toString(36).slice(2,8) ``.

### Decisive source
```ts
// :141-147 + :372-389 — MSSQL rejects agg(subquery); defer to derived table:
// SELECT agg(v) FROM ( SELECT subquery AS __nc_rollup_val FROM related … ) sub
if (baseModelSqlv2.isMssql) {
  qb.select({ [NC_ROLLUP_VAL_ALIAS]: selectColumnName });   // per-row value only
  ...
const wrapMssqlNestedAgg = (innerQb) => {
  if (!(baseModelSqlv2.isMssql && selectColumnIsSubquery)) return innerQb;
  const aggSql = sumFamily ? `COALESCE(${aggInner}, 0)` : aggInner;
  return knex.from(innerQb.as(`${refTableAlias}__agg`))
             .select(knex.raw(aggSql, [NC_ROLLUP_VAL_ALIAS]));
};

// :203-215 — knex.raw(rawObj) RESOLVES the inner Raw first, STRIPPING the
// formula's own '\?' escapes → bare ? collides with outer WHERE bindings
// (soft-delete etc.) and PG dies on an unbound placeholder. Materialize +
// re-escape:
selectColumnName = knex.raw(`(${formulaQb.builder.toQuery().replaceAll('?', '\\?')})`);

// :289-301 — pg boolean sum/avg needs an integer cast
if (baseModelSqlv2.isPg && ['sum','sumDistinct','avgDistinct','avg'].includes(fn)
    && ['bool','boolean'].includes(rollupColumn.dt))
  qb[fn]?.(knex.raw('??::integer', [selectColumnName]));
```

**Flow:** resolve rollup column (+ `parentColumns.cloneAndAdd` for circular-ref tracking) → relation column ⇒ four-context (`getParentChildContext`) → HM/OO: `knex(refTable AS __nc_rollup_x).where(parentPk = refAlias.childFk)` + aliased soft-delete filter → MM: join junction table both ways + soft-delete on the REFERENCED side + `isBtLikeV2Junction` ⇒ `.limit(1)` (single-target V2 semantics) → `applyFunction`: Formula/Created/Modified columns lower through `formulaQueryBuilderv2` with re-escaped `?`; Rollup-of-Rollup recurses (`nestedLevel+1`, same parentColumns); then dialect casts (pg bool::integer, MSSQL bit→FLOAT incl. formula-detected booleans via `selectValueIsBoolean`, Oracle CLOB→VARCHAR2 via `DBMS_LOB.SUBSTR(TO_CLOB(x),4000,1)` for count/min/max of string formulas) → sum family wraps COALESCE(...,0) everywhere except Oracle's hand-written `COALESCE(SUM([distinct ]col),0)`.
**Invariant:** (1) Cross-base rollups read colOptions with `refContext` NOT caller context — wrong base returns null AST and crashes the whole read (:166-179). (2) Sentinel-not-throw: one broken rollup must degrade its own CELL, not fail the query — and partial checks must NEVER write `columnOptions.error` (that flag means "dependency deleted", cleared on restore). (3) Soft-delete filter applies to the AGGREGATED table in every relation shape (child for HM/OO, referenced-parent for MM). (4) The `\?` re-escape is load-bearing for binding integrity.
**Probe:** No unit tests upstream. Deterministic probe: HM rollup renders `(SELECT COUNT(col) FROM child __nc_rollup_x WHERE parent.pk = __nc_rollup_x.fk AND NOT deleted)`; MM+btLikeV2 adds LIMIT 1; error sentinel is literal `'ERR'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "genRollupSelectv2 applyFunction wrapMssqlNestedAgg", limit: 5 });
// genRollupSelectv2 32-565, applyFunction 149-370, wrapMssqlNestedAgg 375-389
```

## Verdict
Adopt: correlated-subquery shape, sentinel failure contract, refContext-for-colOptions cross-base rule, `\?` re-escape, and all four dialect casts. Adapt alias prefixes/randomness. Omit Profiler instrumentation. Caveat: no direct tests at pin; graph ranges verified live.
