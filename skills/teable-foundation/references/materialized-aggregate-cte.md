<!-- capsule-v2 -->
# materialized-aggregate-cte — Why are conditional rollup/lookup CTEs emitted WITH ... AS MATERIALIZED on Postgres?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does the builder stop Postgres from re-computing a conditional aggregate once per outer row?

## Materialize the counts CTE; capability-guard the knex call
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/field-cte-visitor.ts:withCte` (:905-921) + materialization sites (:1500-1533 equality plan, :1568-1581 fallback plan, :1876-1890 conditional lookup).
**Signature:** `private withCte(name, builder: (qb) => void, opts?: { materialized?: boolean })`.
**Data Shape:** `preferMaterializedCte = this.dbProvider.driver === DriverClient.Pg`; duck-typed probe for knex's `withMaterialized`.

### Decisive source
```ts
const qbWithMaterialized = this.qb as Knex.QueryBuilder & {
  withMaterialized?: (alias, expression) => Knex.QueryBuilder;
};
if (opts?.materialized && typeof qbWithMaterialized.withMaterialized === 'function') {
  qbWithMaterialized.withMaterialized(name, builder);
  return;
}
this.qb.with(name, builder);
...
// equality-plan site:
// Materialize to stop Postgres from re-running the aggregate for every outer row
// when the host table is re-joined during UPDATE ... LIMIT pagination.
this.withCte(cteName, ..., { materialized: preferMaterializedCte });
```

**Flow:** every conditional-rollup / conditional-lookup CTE emission passes `{materialized: preferMaterializedCte}` → on PG the planner must run the aggregate once and reuse it across outer-row re-joins → plain `.with` on other drivers or older knex.
**Invariant:** the in-source comment is the porting warning: without MATERIALIZED, an UPDATE...FROM re-join of the host table makes PG inline and RE-EXECUTE the aggregate per row. The duck-type guard means the code degrades silently-but-safely rather than crashing on knex versions lacking the API.
**Probe:** static byte-exact: `grep -n 're-running the aggregate for every outer row' field-cte-visitor.ts` → :1505; `grep -c 'withMaterialized' field-cte-visitor.ts` → 3.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"withMaterialized","limit":5,"detail":"ids"}'
```

## Verdict
Adopt "aggregate side-CLEs are MATERIALIZED by default on PG". Adapt driver gate + knex duck-typing to your stack's API surface. Omit nothing.
