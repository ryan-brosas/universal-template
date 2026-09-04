<!-- capsule-v2 -->
# Stored query builder ordering contract — how do raw column reads reproduce v1 sort semantics for nulls, choices, users, and date-only fields?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** When reading pre-computed columns without laterals, which ORDER BY expressions keep row order identical to the computed path and v1?

## Three-tier ORDER BY resolution in the stored read path
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/stored/StoredTableRecordQueryBuilder.ts` — null-ordering (:168–176), `applyUserLikeOrderBy` (:330+), `applySelectChoiceOrderBy` (:360+), `resolveOrderBy` field routing; helpers `query-builder/dateLikeOrderBy.ts`, `query-builder/userSnapshotSql.ts`; select side `stored/StoredFieldSelectVisitor.ts`; direct test `StoredTableRecordQueryBuilder.spec.ts`.
**Signature:** builder accumulates `orderBy(column: FieldId | SystemColumn, 'asc'|'desc')` then compiles one SELECT over `${tableName} as t` with system columns (`__id, __version, __auto_number, __created_time, __created_by, __last_modified_time, __last_modified_by`) always projected.
**Data Shape:** resolved per-column plan: `{ column, direction, expression?, userLikeMode?, userLikeSource?: 'field'|'system', selectChoiceMode?, selectChoiceOrder? }`.

### Decisive source
```ts
// :168–175 — Postgres default is ASC NULLS LAST / DESC NULLS FIRST; v1 is the opposite.
// Align null ordering with v1: ASC => nulls first, DESC => nulls last.
// Without this ... causing row offset mismatches during paste.
const nullOrderDirection: 'asc' | 'desc' = orderBy.direction === 'asc' ? 'desc' : 'asc';
query = query
  .orderBy(sql`${columnRef} is null`, nullOrderDirection)
  .orderBy(columnRef, orderBy.direction);
```

**Flow:** every ordered column gets a leading `(col IS NULL) <inverted-dir>` key, then the value expression:
1. **user/link fields** sort by title projection — single: `col::jsonb->>'title'`; multiple: `jsonb_path_query_array(array-normalized jsonb, '$[*].title')::text`; system createdBy/lastModifiedBy wrap `to_jsonb()` (may be scalar) with a `coalesce(title,name,#>>'{}')` ladder.
2. **select-choice fields** sort by option position: `ARRAY_POSITION(ARRAY[...option names], value::text)`; multiple-select uses first element via `jsonb_path_query_first(col::jsonb,'$[0]')#>>'{}'`, ties broken by the raw jsonb text.
3. **date-like (date/createdTime/lastModifiedTime) with TimeFormatting.None** sort by display truncation: `to_char(timezone(tz, col), 'YYYY'|'YYYY-MM'|'YYYY-MM-DD')` from the formatting preset (`buildDateLikeOrderExpression` returns null → plain column when time is shown).
4. Lookup-of-singleSelect inherits choice ordering from the INNER field's options (mode defaults multiple unless multiplicity says single).

**Invariants:** stored mode selects computed columns as-is (StoredFieldSelectVisitor projects every field type identically); `sourceTableName` overrides the FROM table for CTE-backed permission views; where specs AND-combine through one visitor with `tableAlias: 't'`.

**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/stored/StoredTableRecordQueryBuilder.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "StoredTableRecordQueryBuilder applyUserLikeOrderBy ARRAY_POSITION", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt inverted-null-first keys and expression-based ordering for enum/json/date columns. Adapt format strings to your locale layer. Omit computed-mode laterals (covered by existing `query-lateral-hydration`).
