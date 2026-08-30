<!-- capsule-v2 -->
# Group-key projection — how does a virtual column become an SQL GROUP BY key, and which types are rejected or silently dropped?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What SQL does each column type compile to as a group key, and what are the exact rejection/drop rules?

## processColumn type ladder
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2/group-by.ts:processColumn` (:144-380); count()-side twin inline (:771-1004).
**Signature:** `processColumn(col: string, isSubGroup = false): Promise<string /* toQuery() */>`; closure over `selectors`, `groupBySelectors`, `groupByColumns`.
**Data Shape:** Group keys are projected under the column's display alias (`getAs`), then referenced by alias in GROUP BY / ORDER BY.

### Decisive source
```ts
// :152-156 — a broken formula/rollup (colOptions.error) is a 400, not a crash:
if (column.colOptions?.error) {
  NcError.get(baseModel.context).badRequest(
    `Cannot group by column '${column.title}': ${column.colOptions.error}`);

// :159-166 — QR/barcode group by their VALUE column while keeping the original
// alias (asId) so the response shape is unchanged:
if ([UITypes.QrCode, UITypes.Barcode].includes(column.uidt)) {
  column = new Column({ ...(await column.getColOptions<...>(...)
    .then((col) => col.getValueColumn(baseModel.context))), asId: column.id });

// :176-184 — hard rejections:
case UITypes.Attachment: // badRequest 'Group by using attachment column is not supported'
case UITypes.Button:     // badRequest '...Button column is not supported'

// :321-338 — JSON: pg compiles (col)::jsonb, EVERY OTHER DIALECT falls out of
// the switch with NO selector and NO error → the JSON key is silently ABSENT
// from grouping on mysql/mssql/sqlite/oracle. Silent-drop by design.
case UITypes.JSON:
  if (baseModel.dbDriver.clientType() === 'pg') { /* only pg pushes a selector */ }

// :360-377 — default branch wraps every plain column in sqlNullIfBlank so
// NULL and '' collapse into one bucket (see groupby-blank-null-buckets):
const defaultColumnNameQb = sqlNullIfBlank({ columnName: defaultColumnName, baseModel });
```
Lookup/LTAR keys wrap `generateLookupSelectQuery(...).builder` in `raw(...).wrap('(',')')` (:244-251); rollup uses `genRollupSelectv2(...).builder` (:188-199); datetime truncates to MINUTE per dialect (see groupby-datetime-minute-bucketing).

**Flow:** find column by column_name OR title → reject errored meta → QR/Barcode swap-to-value-column keeping alias → switch on uidt pushing into `selectors` (+ registering alias in `groupByColumns`) → return `.toQuery()` (ALWAYS raw string, needed by the sub-group path).
**Invariant:** (1) Rejections are explicit for Attachment/Button but JSON-on-non-pg is a SILENT drop — porters who "fix" this change product behavior. (2) The QR/Barcode swap preserves the outer alias, so clients never see the value column's name. (3) `toQuery()` return isn't incidental: the sub-group expression path consumes it as a string.
**Probe:** No unit tests upstream. Deterministic probe: grouping by a JSON column on sqlite yields SQL without that key and no error; on pg yields `(col)::jsonb`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "processColumn", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.group-by.processColumn Function group-by.ts 144-380
```

## Verdict
Adopt the per-type key ladder incl. silent non-pg JSON drop and QR/Barcode value-swap-with-alias. Adapt type enum to host. Caveat: no direct tests at pin; graph range verified live.
