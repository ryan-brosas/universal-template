<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/cross-db-utils/applyAggregation.ts` (whole, 138L).

# Question
What must happen BEFORE a (column, aggregation) pair reaches the dialect SQL generator?

## Path / Symbol
`applyAggregation({ baseModelSqlv2, aggregation, column, alias?, baseQuery? }) → Promise<string | undefined>`

## Signature
Returns the final SQL fragment string (COALESCE+alias already applied by the handler's wrap) or `undefined`.

## Decisive source
applyAggregation.ts:45–51 — two silent-skip gates FIRST: missing aggregation/column ⇒ undefined; **`column.colOptions?.error` ⇒ undefined** (a stored formula/column compile error silently excludes the column from aggregation rather than 500-ing the whole request).
:67–74 — `validateAggregationColType(column, aggregation)` (SDK) classifies into common/numerical/boolean/date/attachment/unknown; `false | 'unknown'` ⇒ `NcError.notImplemented('Aggregation X is not implemented yet')`. Note the asymmetry with :49: a TYPE-AGG mismatch throws while an errored column skips.
:77–84 — Barcode/QrCode columns are SWAPPED for their underlying value column (`getColOptions(...).getValueColumn(context)`), keeping the ORIGINAL column id (:82 `id: column.id`) so result keys still match the requested column.
:95–101 — virtual columns (Links/Rollup/Lookup/Formula/LTAR) resolve their SELECT expression via `getColumnNameQuery(...).builder` instead of a physical name.
:105–122 — pg numeric-formula IEEE guard: when uidt=Formula ∧ parsedFormulaType=NUMERIC ∧ isPg ∧ aggregation ∈ NumericalAggregations ∧ builder isn't a string, the expression is wrapped in `excludeNonFiniteSql('??')` bound TWICE ("mentions the expression twice, so it needs two binds"). The comment pins WHY: one NaN would take SUM/AVG/MAX for the whole column; count family deliberately keeps Infinity rows ("an Infinity cell is not empty").
:124 — dispatch via `DBQueryClient.fromKnex(baseModelSqlv2.dbDriver).generateAggregateQuery(params)` — the factory-from-knex form so EE dialects throw here.

## Flow / Invariant
Ordering contract: skip-gates → validate(throw) → virtual-column unwrap → expression resolve → IEEE guard → dispatch. Reordering any pair changes observable behavior (e.g. validating before the error-check turns stored formula errors into 501s).

## Probe (direct test)
From repo root:
```
sed -n '45,51p' packages/nocodb/src/dbQueryClient/cross-db-utils/applyAggregation.ts | grep -c 'return;'   # => 2 silent-skip gates
grep -c 'notImplemented' packages/nocodb/src/dbQueryClient/cross-db-utils/applyAggregation.ts             # => 2 (:35 doc comment + :70 call)
grep -c "isPg" packages/nocodb/src/dbQueryClient/cross-db-utils/applyAggregation.ts                       # => 1 (:113)
grep -n 'getValueColumn' packages/nocodb/src/dbQueryClient/cross-db-utils/applyAggregation.ts             # => 1 (:81)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"applyAggregation validateAggregationColType","limit":2,"detail":"compact"}'
```
→ `...applyAggregation.applyAggregation Function ... applyAggregation.ts 38-136`.

## Verdict
**Adopt.** This prelude is the single entry every aggregate consumer shares; its gate order IS the API contract.
