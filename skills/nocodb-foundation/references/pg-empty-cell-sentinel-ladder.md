<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts` :17–57 (buildContext) + :59–276 (common family).

# Question
What counts as "empty" per column type in PostgreSQL aggregation — and why does the sentinel differ between dialects?

## Path / Symbol
`PgAggregationHandler.buildContext(params)` → `condnValue`; consumed by CountEmpty/CountFilled/CountUnique/Percent* SQL.

## Signature
```ts
protected buildContext(params: AggregationGeneratorParams): AggregationSqlContext
// ctx.condnValue ∈ { "''" (default), NULL (typed columns), 0 (Rating) }
```

## Data Shape
condnValue is interpolated RAW into SQL text (`= ${condnValue}`), not bound — it is a compile-time constant chosen by column class.

## Decisive source
pg.handler.ts:23–26 — default sentinel is the SQL literal `''`; but **native PG enum columns reject `''` with "invalid input value for enum"** and an enum cell can't hold '' anyway, so `isNativePgEnum = !!column.internal_meta?.pg_enum_type_name` forces the NULL sentinel (:26). This is the pg-ONLY branch — mysql/sqlite handlers have no enum concept.
:28–51 — numeric/date/system families (CreatedTime…UUID, Rollup, Links, ID) + DATE/NUMERIC formula types ⇒ `'NULL'`.
:52–54 — Rating ⇒ `0`: a zero-star rating IS an empty cell.
Consumer shape (:76–79): `COUNT(*) FILTER (WHERE (??) IS NULL OR (??) = ${condnValue})` — the same condnValue doubles as the filled-test comparator in CountFilled (:119–122): `IS NOT NULL AND (??) != ''`.

## Flow / Invariant
Porter trap: the empty-cell predicate is THREE-way per column type — pure NULL for typed columns (comparing numbers to '' is either an error or always-false depending on dialect cast rules), `= ''` for string-ish cells, `= 0` for ratings. Porters who collapse this to a single `IS NULL` change every percent-empty statistic on string and rating columns. The pg FILTER clause is itself the dialect marker — mysql/sqlite express identical predicates as SUM(CASE...) instead.

## Probe (direct test)
From repo root:
```
sed -n '28,50p' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | grep -c 'UITypes\.'   # => 16 in buildContext's list
grep -n 'pg_enum_type_name' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts            # => 1 (:26)
sed -n '46,54p' packages/nocodb/src/dbQueryClient/aggregations/handlers/pg.handler.ts | grep -c 'condnValue ='   # => 2 assignments ('NULL' :51, 0 :53) after the "''" default at :23
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"PgAggregationHandler buildContext condnValue enum","limit":2,"detail":"compact"}'
```
→ `...pg.handler.PgAggregationHandler.buildContext ... pg.handler.ts 17-57`.

## Verdict
**Adapt.** Port the three-tier sentinel ladder; re-map the typed-column list to your own schema's type system and keep the native-enum escape hatch if your target has enum types.
