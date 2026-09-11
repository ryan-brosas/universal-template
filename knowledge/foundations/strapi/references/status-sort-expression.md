<!-- capsule-v2 -->
# Status sort expression — how do you sort rows by a computed draft/modified/published status without a stored column?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** How does a virtual `status` sort key become valid SQL — including under `SELECT DISTINCT` where PostgreSQL rejects ORDER BY expressions missing from the SELECT list?

## Status-sort seam
**Path/Symbol:** `packages/core/database/src/query/helpers/order-by.ts:buildStatusSortExpression` (lines 30–47), `toKnexOrderByDescriptor` (60–75), `processOrderBy` status gate (76–101); `packages/core/database/src/query/query-builder.ts:processSelect` DISTINCT injection (559–582), `getKnexQuery` orderBy emission (722–730).
**Signature:** `buildStatusSortExpression(db, tableName, tableAlias, isI18n = false): Knex.Raw`; `toKnexOrderByDescriptor(db, tableName, rootTableAlias, entry: OrderByValue): { column: string | Knex.Raw; order?: 'asc' | 'desc' }`.
**Data Shape:** input is the processed `OrderByValue[]` from `processOrderBy`; the virtual entry is `{ rawExpression: 'status', isI18n, order }`. The CASE rank: 0 = no published sibling with same `document_id` (+locale), 1 = draft `updated_at` > MAX published `updated_at`, 2 = published.

### Decisive source
```ts
// order-by.ts — parameterized correlated subqueries; locale guard only for i18n models
const localeCondition = isI18n ? ` AND sub.locale = ${tableAlias}.locale` : '';

return db.connection.raw(
  `CASE WHEN NOT EXISTS(SELECT 1 FROM ?? sub WHERE sub.document_id = ${tableAlias}.document_id AND sub.published_at IS NOT NULL${localeCondition}) THEN 0 WHEN ${tableAlias}.updated_at > (SELECT MAX(sub.updated_at) FROM ?? sub WHERE sub.document_id = ${tableAlias}.document_id AND sub.published_at IS NOT NULL${localeCondition}) THEN 1 ELSE 2 END`,
  [tableName, tableName]
);
```
```ts
// query-builder.ts processSelect — PostgreSQL requires every ORDER BY expression in the
// SELECT list when SELECT DISTINCT is used; raw expressions are added explicitly using the
// same builder/alias as the ORDER BY so the rendered SQL matches
const rawOrderByExpressions = state.orderBy
  .filter((ob: any) => 'rawExpression' in ob)
  .map((ob: any) => helpers.buildStatusSortExpression(db, tableName, this.alias, ob.isI18n));

state.select = [...state.select, ...rawOrderByExpressions];
```
```ts
// processOrderBy — the virtual key is gated on model capability
if (orderBy === 'status') {
  if (!attributes.publishedAt || !attributes.documentId) {
    throw new Error(`Cannot order by status on model ${uid}: missing publishedAt or documentId`);
  }
  const isI18n = 'locale' in attributes;
  return [{ rawExpression: 'status' as const, isI18n, order: undefined }];
}
```

**Flow:** user passes `sort: 'status'` or `{ status: 'asc' }` → `processState()` runs `processOrderBy`, which validates the model has BOTH `publishedAt` and `documentId` attributes and derives `isI18n` from attribute presence → emits the raw-expression entry → `processSelect()` appends the identical CASE expression to the select list whenever `shouldUseDistinct()` (joins present, no groupBy) → `getKnexQuery()` maps every entry through `toKnexOrderByDescriptor`, which hands the `Knex.Raw` straight into knex's compound `orderBy` (runtime-accepted despite typings listing only string).
**Invariant:** the table name is bound via knex `??` placeholders, never string-interpolated; the SAME expression shape built with the SAME alias must appear in both SELECT and ORDER BY under DISTINCT (mismatched rendering is exactly regression #26746); i18n models must carry the `sub.locale = alias.locale` condition or cross-locale siblings corrupt the rank.
**Probe:** `tests/api/core/content-manager/api/status-sort-relation-filter.test.api.ts` (#26746 regression: `sort: 'status:ASC'` + relation filter on a non-id field returns 200 with JOIN + DISTINCT + CASE; ascending puts the draft row first; filter-only and sort-only requests still succeed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "buildStatusSortExpression status sort expression", file_pattern: "packages/core/database/src/query/*", limit: 10, fields: ["signature", "name", "file"] });
```
Pass 3 note: Codebase Memory MCP was not connected in this session; the cited ranges were confirmed by direct read of the checkout at the pinned HEAD instead (see verification.md).

## Verdict
Adopt the computed-rank pattern: keep the status derivation in SQL (correlated subqueries over `document_id`), gate the virtual key on the attributes that make it computable, and duplicate raw ORDER BY expressions into the DISTINCT select list. Adapt the rank semantics (draft/modified/published thresholds) and the i18n locale guard to your own document model. Omit Strapi's `document_id`/`published_at` column names and the knex `??` binding style specifics. Coverage caveat: no unit test exists for `order-by.ts` itself; the contract is pinned by the #26746 API regression test plus the deep-sort suite.
