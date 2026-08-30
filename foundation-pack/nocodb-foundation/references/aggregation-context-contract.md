<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/types.ts` :12–22 (`AggregationGeneratorParams`) + `aggregations/aggregation-handler.interface.ts` :26–61 (`AggregationSqlContext`).

# Question
What is the exact data contract flowing from prelude to dialect handler, and which fields are dialect-optional?

## Path / Symbol
`AggregationGeneratorParams` (caller→handler) and `AggregationSqlContext` (handler-internal; each dialect buildContext returns the flat spread — generic.ts carries no condnValue).

## Signature
```ts
interface AggregationGeneratorParams {
  column: Column; baseModelSqlv2: IBaseModelSqlv2; aggregation: string;
  column_query: string | Knex.QueryBuilder;
  parsedFormulaType?: FormulaDataTypes; aggType: AggregationCategory;
  alias?: string; baseQuery?: Knex.QueryBuilder;
}
interface AggregationSqlContext extends params-fields {
  knex: CustomKnex; condnValue?: any; cq?; subAggFrom?; subAggCol?;
  materialize?: boolean; derivedInner?: Knex.QueryBuilder;   // mssql/oracle only
}
```

## Data Shape
Two optional fields carry the whole materialization story: `baseQuery` (caller's filtered builder — mysql/sqlite clone it into nc_agg_sub) and `alias` (single-mode col.id vs bulk bucket key). The context adds `cq/subAggFrom/subAggCol` for self-contained-subquery dialects and `materialize/derivedInner` documented as "mssql/oracle: whether the column was materialized into a derived table" — fields the CE build never populates.

## Decisive source
aggregation-handler.interface.ts:43–44 — `condnValue` doc: 'Dialect "empty" sentinel used by count-empty / count-filled predicates' — optional BECAUSE pg computes it in buildContext while the interface stays buildable without it.
:46–50 — `cq` doc: 'Plain dialects use column_query; mssql/oracle point this at the materialized nc_val when a virtual column is involved' — the EE handlers rewrite WHICH expression the category methods aggregate over without changing their SQL text.
types.ts:17 — `column_query: string | Knex.QueryBuilder` — the union IS the virtual/physical fork: string = raw column name (physical), builder = compiled virtual-column SELECT (from getColumnNameQuery).
Each dialect's `buildContext()` returns the ONE-flat-object spread itself (`{...params, knex, condnValue}` — pg.handler.ts:56; mysql.handler.ts:73 and sqlite.handler.ts:73 add subAggFrom/subAggCol); generic.ts carries NO condnValue — no getter indirection anywhere on this path.

## Flow / Invariant
Contract rule: everything a category method needs must arrive through AggregationSqlContext; nothing reads module state. That is what makes handlers instantiable per-call (`new HandlerClass()` in getAggregationHandler) with zero shared mutable state across concurrent aggregations — porters who add handler-level caching introduce cross-request leakage under Promise.all fan-out.

## Probe (direct test)
From repo root:
```
grep -c 'materialize' packages/nocodb/src/dbQueryClient/aggregations/aggregation-handler.interface.ts   # => 4 (:57 field + 3 doc mentions)
grep -c 'derivedInner' packages/nocodb/src/dbQueryClient/aggregations/aggregation-handler.interface.ts  # => 1 (:60 field)
grep -n 'subAggFrom?\|subAggCol?' packages/nocodb/src/dbQueryClient/aggregations/aggregation-handler.interface.ts       # => 2 field decls (:53,:55)
grep -rn '\.\.\.params, knex, condnValue' packages/nocodb/src/dbQueryClient/aggregations/handlers/ | wc -l            # => 3 buildContext spreads (pg :56, mysql :73, sqlite :73)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"AggregationGeneratorParams AggregationSqlContext","limit":3,"detail":"compact"}'
```
→ resolves both interfaces line-exact.

## Verdict
**Adopt.** Port both interfaces verbatim — they are the seam contract that keeps handlers stateless.
