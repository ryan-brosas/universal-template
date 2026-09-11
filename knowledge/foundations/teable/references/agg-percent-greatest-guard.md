<!-- capsule-v2 -->
# Percent-family GREATEST guard — why every percentage divides by GREATEST(COUNT(*), 1)

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How do the percent aggregates avoid division-by-zero and keep exact 0/100 bounds on empty tables?

## GREATEST denominator + complement numerators
**Path/Symbol:** `apps/nestjs-backend/src/db-provider/aggregation-query/postgres/aggregation-function.postgres.ts` — `percentEmpty` (:52–56), `percentFilled` (:58–62), `percentUnique` (:18–32), `percentChecked` (:78–84), `percentUnChecked` (:86–92).
**Signature:** each returns raw SQL text; all share `(numerator * 1.0 / GREATEST(COUNT(*), 1)) * 100`.
**Data Shape:** numeric percent [0,100]; COUNT(*) = row count in current scope (post-filter, post-group).

### Decisive source
```ts
percentEmpty(): string {
  return this.knex
    .raw(`((COUNT(*) - COUNT(${this.tableColumnRef})) * 1.0 / GREATEST(COUNT(*), 1)) * 100`)
    .toQuery();
}
percentFilled(): string {
  return this.knex
    .raw(`(COUNT(${this.tableColumnRef}) * 1.0 / GREATEST(COUNT(*), 1)) * 100`)
    .toQuery();
}
```

**Flow:** Empty/Filled are complements computed from `COUNT(col)` (non-null count) vs `COUNT(*)`; UnChecked counts `false OR NULL` so unchecked-empty rows land on the unchecked side; Unique uses `COUNT(DISTINCT col)`.
**Invariant:** Three porters-get-wrong details: (1) `* 1.0` BEFORE division forces decimal math — integer division would floor every percent to 0. (2) `GREATEST(COUNT(*), 1)` keeps empty tables/groups at 0 instead of NULL/error while never distorting non-zero denominators. (3) COUNT(col) skips NULLs, so "filled" is defined as non-null, NOT truthy — a jsonb `'[]'` still counts as filled; emptiness of array CONTENTS is a UI concern. The service's `defaultToZero` list (`aggregation.service.ts:218–224`) then maps a NULL result to 0 for exactly these five percent funcs client-side.
**Probe:** `grep -cF 'GREATEST(COUNT(*), 1)' apps/nestjs-backend/src/db-provider/aggregation-query/postgres/aggregation-function.postgres.ts` → 6.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "percentFilled percentEmpty GREATEST COUNT", limit: 10 });
```

## Verdict
Adopt GREATEST-guarded denominators + pre-division float promotion for any percent-of-rows aggregate; adapt the numerator definitions to your null semantics.
