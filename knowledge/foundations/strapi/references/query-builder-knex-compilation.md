<!-- capsule-v2 -->
# Query-builder → knex compilation — how do you compile a DB-agnostic query DSL into one SQL query without breaking join-based filters or pagination?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** Where must sub-query rewriting happen so UPDATE/DELETE that reference joins stays valid SQL, and when does an insert need RETURNING?

## Query-builder compilation seam
**Path/Symbol:** `packages/core/database/src/query/query-builder.ts:getKnexQuery` (lines 585–737), with `shouldUseSubQuery` (434–436), `runSubQuery` (438–448), `init` (327–379).
**Signature:** `getKnexQuery(): Knex.QueryBuilder` on a closure-scoped builder object carrying `state` (`type`, `select`, `where`, `search`, `joins`, `orderBy`, `limit/offset/first`, `transaction`, `onConflict`, `increments/decrements`).
**Data Shape:** `state.type ∈ select|count|max|min|insert|update|delete|truncate`; joins accumulate before compilation; alias resolution via `mustUseAlias()` → `"table as alias"`.

### Decisive source
```ts
// The state should always be processed before calling shouldUseSubQuery as it
// relies on the presence or absence of joins to determine the need of a subquery
this.processState();

if (this.shouldUseSubQuery()) {
  return this.runSubQuery();
}
...
case 'insert': {
  qb.insert(state.data);
  if (db.dialect.useReturning() && _.has('id', meta.attributes)) {
    qb.returning('id');
  }
```
```ts
shouldUseSubQuery() {
  return ['delete', 'update'].includes(state.type) && state.joins.length > 0;
},
runSubQuery() {
  const originalType = state.type;
  this.select('id');
  const subQB = this.getKnexQuery();
  const nestedSubQuery = db.getConnection().select('id').from(subQB.as('subQuery'));
  const connection = db.getConnection(tableName);
  return (connection[originalType] as Knex)().whereIn('id', nestedSubQuery);
},
```

**Flow:** `.init(params)` normalizes user params into `state` → caller chains typed setters → `getKnexQuery()` runs `processState()` (normalizes orderBy to `OrderByValue[]`, decides distinct/subquery) → type switch emits the base operation → transaction/lock/onConflict/limit/offset/groupBy applied → where → search → **joins before root orderBy** (join-table ordinal must precede root `id ASC` stability sort or relation ordering breaks pagination) → optional deep-sort wrap.
**Invariant:** `processState()` must run before the sub-query decision (join presence drives it); join `orderBy` entries must be emitted into knex before root `orderBy`; `returning('id')` only when both dialect supports it and the model has an `id` attribute.
**Probe:** `packages/core/database/src/__tests__/index.test.ts` (`useReturning` connection flag, line 46) plus integration coverage in `tests/api/core/database/db.test.api.js` — pins that insert id extraction depends on the dialect returning path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "query builder create", file_pattern: "packages/core/database/src/query/*", limit: 25 });
```
Executed during pass 1: returned 136 total matches led by `createQueryBuilder` (131–783), `getKnexQuery`, `runSubQuery`, `init`.

## Verdict
Adopt the compile-once state machine and the update/delete-with-joins `whereIn(id, subquery)` rewrite — it is the portable fix for SQL engines rejecting UPDATE...JOIN. Adapt dialect gates (`useReturning`) and the join-order-before-root-order emission to your SQL builder's API. Omit Strapi metadata plumbing (`meta.attributes` lookups) and deep-sort wrapping unless you port that feature too. Coverage: `no_recorded_issue` + `metadata_match` for `query-builder.ts`.
