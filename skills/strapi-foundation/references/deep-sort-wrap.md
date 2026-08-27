<!-- capsule-v2 -->
# Deep-sort row-number wrap — how do you paginate correctly when sorting by joined-relation columns?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** Sorting by a column of a joined relation duplicates parent rows (one per joined row); how do you dedupe per parent while keeping the sort order and pagination correct?

## Deep-sort seam
**Path/Symbol:** `packages/core/database/src/query/helpers/order-by.ts:wrapWithDeepSort` (lines 166–318), `getStrapiOrderColumnAlias` (155–160); `packages/core/database/src/query/query-builder.ts:shouldUseDeepSort` (522–548), `ensurePaginationOrderStability` (486–516).
**Signature:** `wrapWithDeepSort(originalQuery: Knex.QueryBuilder, ctx: OrderByCtx): Knex.QueryBuilder`; trigger `shouldUseDeepSort(): boolean` — true when any dotted orderBy column references a relation attribute or a join alias.
**Data Shape:** three query layers — baseQuery (filtered, unsorted), T (numbered partitions), resultQuery (deduped, paginated, sorted). Sort columns are aliased `__strapi_order_by__<col with dots as underscores>`; the partition key is `__strapi_row_number`.

### Decisive source
```ts
// order-by.ts — the sub-query keeps filters but loses select/order/pagination;
// only id + aliased sort columns survive into it
baseQuery
  .clear('select')
  .clear('order')
  .clear('limit')
  .clear('offset');

baseQuery.select(
  prefix(qb.alias, 'id'),
  ...columnOrderBy.map((orderByClause) =>
    alias(getStrapiOrderColumnAlias(orderByClause.column), orderByClause.column)
  )
);
```
```ts
// T: one row number per parent id, ordered by the sort columns
.rowNumber(COL_STRAPI_ROW_NUMBER, (subQuery) => {
  for (const orderByClause of prefixedOrderBy) {
    subQuery.orderBy(orderByClause.column, orderByClause.order, 'last');
  }
  subQuery.partitionBy(`${baseQueryAlias}.id`);
})
```
```ts
// resultQuery: inner join keeps only each partition's first row; pagination re-applied outside
.on(`${partitionedQueryAlias}.id`, `${resultQueryAlias}.id`)
.andOnVal(`${partitionedQueryAlias}.${COL_STRAPI_ROW_NUMBER}`, '=', 1);
...
if (qb.state.limit) { resultQuery.limit(qb.state.limit); }
if (qb.state.offset) { resultQuery.offset(qb.state.offset); }
...
// final sort: T-prefixed sort aliases, raw expressions rebuilt with the OUTER alias,
// then a primary-key tie-breaker for exact-equal rows
{ column: `${partitionedQueryAlias}.id`, order: 'asc' },
```

**Flow:** `getKnexQuery()` builds the normal query (filters, joins, search) → `shouldUseDeepSort()` detects a dotted orderBy column whose prefix is a relation attribute or a join alias → `wrapWithDeepSort` clones the original as baseQuery, clears select/order/limit/offset, re-selects `id` + aliased sort columns → builds T with `row_number() OVER (PARTITION BY <alias>.id ORDER BY <sort cols>)` → resultQuery inner-joins T on id where `row_number = 1`, re-applies limit/offset/first OUTSIDE, re-emits the sort against T aliases (raw status expressions rebuilt with the outer alias), and appends `T.id ASC` as a deterministic tie-breaker.
**Invariant:** filtering must stay in the deepest sub-query (moving WHERE outward corrupts which rows are partitioned); pagination must move to the outer query or rows are pruned before dedup; dedup happens via `row_number = 1`, not DISTINCT; deep-sorted queries skip `ensurePaginationOrderStability` because the wrap already appends its own tie-breaker; raw-expression sorts must be rebuilt against the OUTER alias inside the wrap or they reference a table that no longer exists in scope.
**Probe:** `tests/api/core/strapi/api/sort/sort.test.api.ts` — deep sort at 1st and 2nd level, mixed deep+regular sort arrays, pagination via both `start/limit` and `page/pageSize` (with meta.pagination totals), deep sort + shallow filters, and an explicit `test.skip` documenting that deep sort + DEEP filter is unsupported (where and orderBy would bind to different joins).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "wrapWithDeepSort rowNumber partitionBy", file_pattern: "packages/core/database/src/query/*", limit: 10, fields: ["signature", "name", "file"] });
```
Pass 3 note: Codebase Memory MCP was not connected in this session; the cited ranges were confirmed by direct read of the checkout at the pinned HEAD instead (see verification.md).

## Verdict
Adopt the three-layer pattern (filter-deep / number-partitions / paginate-outside) for any SQL engine without window-function-free alternatives — it is the portable answer to "sort by a child's column, return parents". Adapt the alias prefixes (`__strapi_order_by__*`, `__strapi_row_number`) to your namespace, and the tie-breaker column to your primary key. Omit Strapi's join-alias detection heuristics tied to its metadata shape. Coverage caveat: no unit test for `order-by.ts`; behavior is pinned by the API-level sort suite, including the documented deep-filter limitation.
