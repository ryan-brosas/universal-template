<!-- capsule-v2 -->
# query chain toSql pipeline — how does a fluent builder turn into SQL with unbounded-DML guards?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What is the object chain from `Query.from(...)` to a SQL string, and which guards stop accidental full-table deletes/updates?

## Four-class builder pipeline
**Path/Symbol:** `packages/pg-meta/src/query/Query.ts` (:7-17) → `QueryAction.ts` (:14-73) → `QueryFilter.ts` (:10-77) → `QueryModifier.ts` (:17-97); guards in `Query.utils.ts` (`deleteQuery` :48-50, `updateQuery` :152-154, `insertQuery` :77-79).
**Signature:** `new Query().from(name, schema?) → QueryAction.count/delete/insert/select/update/truncate(...) → QueryFilter.filter/match/order/range → toSql({isCTE, isFinal})`.
**Data Shape:** QueryAction is stateless (holds only `{name, schema: schema ?? 'public'}`); QueryFilter accumulates `filters[]`, `sorts[]`, actionConfig; QueryModifier is a throwaway projection built fresh per terminal call.

### Decisive source
```ts
// QueryFilter — mutation-safe reuse
clone(): QueryFilter {
  const clonedData = structuredClone({
    table: this.table, actionConfig: this.actionConfig,
    actionOptions: this.actionOptions, filters: this.filters, sorts: this.sorts,
  })
  const cloned = new QueryFilter(clonedData.table, clonedData.actionConfig, clonedData.actionOptions)
  cloned.filters = clonedData.filters
  cloned.sorts = clonedData.sorts
  return cloned
}
```
```ts
// Query.utils deleteQuery / updateQuery head — the unbounded-DML guard
if (!filters || filters.length === 0) {
  throw new Error('no filters for this delete query')   // update twin: 'no filters for this update query'
}
```
```ts
// QueryModifier.range — inclusive-both-ends arithmetic
range(from: number, to: number) {
  this.pagination = { offset: from, limit: to - from + 1 }
  return this
}
```

**Flow:** `from()` defaults schema to `'public'` → verb method picks action + options (returning, enumArrayColumns) → filter/match/order accumulate mutable arrays (`match(criteria)` expands to one `=` filter per entry) → each terminal call constructs a FRESH `QueryModifier` via `_getQueryModifier()` projecting private arrays into its options → `toSql` switches on action and delegates to the Query.utils builders; `range(from,to)` becomes `limit ${literal(to-from+1)} offset ${literal(from)}`.
**Invariant:** delete/update REFUSE to emit SQL without ≥1 filter — the guard lives in the SQL builder, not the UI, so no caller path can bypass it. `toSql` never mutates the QueryFilter; clone() deep-copies via structuredClone so derived queries can diverge safely.
**Probe:** `test/query/advanced-query.test.ts:119-128` pins the snapshot `"select * from public.\"table with spaces\";"` from `new Query().from('table with spaces', 'public').select().toSql()` — DB-backed (live Postgres required; read directly, not executed in-lane). Guard behavior has no dedicated unit test (coverage caveat).
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "Query class filter toSql applyFilters queryTable from modifier range count insert delete update", limit: 15 })
// QueryModifier.toSql :44-97 rank 4, QueryFilter._getQueryModifier rank 9, Query.from :12-17 rank 13
```

## Verdict
Adopt the four-class split (entry / verbs / accumulated clauses / per-call compiler) and the builder-level DML guard. Adapt `match()` expansion and schema defaulting to your host's conventions. Omit the empty `catch (error) { throw error }` in QueryModifier.toSql — it is dead weight, not contract.
