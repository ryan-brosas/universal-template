<!-- capsule-v2 -->
# LinkTitleFill — SQL-side COALESCE of missing link titles from the foreign table

**Source:** teable (AGPL) `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When a link write carries IDs but not titles and `fillLinkTitles` is on, how does teable fill titles in SQL without a second round trip?

## Link title fill expression
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/buildFilledLinkValueExpression.ts` (whole file, 1-75).
**Signature:** `buildFilledLinkValueExpression({linkField, linkItems, fillLinkTitleForeignTables?}): Result<RawBuilder | null, DomainError>`.
**Data Shape:** `MAX_FILLED_LINK_VALUE_ITEMS = 20_000`. Requires the foreign table's `dbTableName` and the lookup field's `dbFieldName` (both Result-unwrapped). Returns a `RawBuilder` SQL expression or `null` when the foreign table isn't in the provided map.

### Decisive source
```ts
// multiple-value: aggregate with per-item title COALESCE against the foreign table's lookup column
return ok(sql`(
  SELECT COALESCE(
    jsonb_agg(jsonb_build_object(
      'id', v.id,
      'title', COALESCE(v.title, ${sql.ref(`ft.${lookupDbFieldName}`)}::text)
    ) ORDER BY v.ord), '[]'::jsonb)
  FROM (VALUES ${valuesSql}) AS v(id, title, ord)
  LEFT JOIN ${sql.table(foreignDbTableName)} ft ON ft.__id = v.id
)`);
```

**Flow:** look up the foreign table in `fillLinkTitleForeignTables` (keyed by foreignTableId string) → if absent return null (caller falls back to plain JSON.stringify of stored value) → enforce the 20k multi-item cap (error) → build a `(VALUES ...) LEFT JOIN foreignTable` subquery that keeps the caller-supplied title when present, else pulls the lookup column's text from the joined row. Single-value variant builds one `(id, title)` row.

**Invariant:** The fill is a pure SQL expression (no async), so it composes inside the single main UPDATE; the cap is enforced BEFORE compiling (validation error, not SQL failure); when the foreign table is unknown the write degrades to storing the raw value rather than failing.

**Probe:** `record/visitors/CellValueMutateVisitor.spec.ts` — `'fills missing link titles using the foreign table dbTableName instead of tableId'` (:354), `'rejects oversized multi-link title fill writes before compiling SQL'` (:400).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildFilledLinkValueExpression jsonb_agg COALESCE title", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the SQL-side title fill, the foreign-table-map lookup, and the 20k pre-compile cap. Adapt the lookup-column naming. Omit nothing portable. Probes pinned to the real spec suite.
