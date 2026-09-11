<!-- capsule-v2 -->
# filter compiler ladder — how do structured filters become a WHERE clause without string concatenation?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** How are operator/value filter objects compiled into safe SQL, including `is null`, LIKE operators, tuple comparisons, and ARRAY[...] literals?

## Structured-filter compiler
**Path/Symbol:** `packages/pg-meta/src/query/Query.utils.ts` : `applyFilters` (:186-224), `inFilterSql` (:226-235), `defaultTupleFilterSql` (:237-257), `inTupleFilterSql` (:259-295), `isFilterSql` (:297-308), `castColumnToText` (:310-312), `filterLiteral` (:395-407), `parseArrayLiteral` (:314-393).
**Signature:** `function applyFilters(query: SafeSqlFragment, filters: Filter[])` — private; reached via the query builders (`selectQuery`, `countQuery`, `deleteQuery`, `updateQuery`).
**Data Shape:** `Filter = { column: string | string[], operator: FilterOperator, value: any }`. Output fragments are joined with `' and '` inside `safeSql`.

### Decisive source
```ts
switch (filter.operator) {
  case 'in':  return inFilterSql(filter)
  case 'is':  return isFilterSql(filter)
  case '~~': case '~~*': case '!~~': case '!~~*':
    return castColumnToText(filter)          // ident(column)::text OP value
  default:
    return safeSql`${ident(filter.column)} ${filter.operator as SafeSqlFragment} ${filterLiteral(filter.value)}`
}
```
```ts
function isFilterSql(filter: Filter) {
  const filterValueTxt = String(filter.value)
  switch (filterValueTxt) {
    case 'null': case 'false': case 'true': case 'not null':
      return safeSql`${ident(filter.column)} ${filter.operator as SafeSqlFragment} ${filterValueTxt as SafeSqlFragment}`
    default:
      return safeSql`${ident(filter.column)} ${filter.operator as SafeSqlFragment} ${filterLiteral(filter.value)}`
  }
}
```

**Flow:** empty filters → query unchanged · array column → tuple arm (operator restricted: `in` or the six comparison ops, others throw; every tuple row length-checked against column arity) · per-operator dispatch as above · `filterLiteral`: boolean → bare true/false; string starting with `ARRAY[` → quote-aware `parseArrayLiteral` scanner (tracks `''` escapes to find the closing bracket, validates cast suffix against `/^::([A-Za-z_][A-Za-z0-9_]*)(\[\])?$/`, unquotes items then re-escapes each through `literal()`); anything else → `literal()`.
**Invariant:** the ONLY free-text that survives is the whitelisted `is` values and validated `ARRAY[...]` syntax — everything user-shaped passes through `ident()`/`literal()` re-escaping. The `::text` cast for LIKE-family operators is semantic, not cosmetic: pattern matching must compare text regardless of column type.
**Probe:** `packages/pg-meta/test/pg-format.test.ts` pins the escaping primitives this compiler leans on; the compiler itself is exercised by `test/query/advanced-query.test.ts` inline snapshots (e.g. `"select * from public.\"table with spaces\";"`) — DB-backed suite requires live Postgres at localhost:5432 (not executable in-lane; anchors verified by direct read).
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "Query class filter toSql applyFilters queryTable from modifier range count insert delete update", limit: 25 })
// applyFilters :186-224 rank 1, QueryFilter.toSql rank 3, QueryModifier.toSql :44-97 rank 4
```

## Verdict
Adopt the dispatch-table + re-escape-everything discipline and the ARRAY-literal parser's "validate-or-fall-back-to-literal" posture — falling back safely beats rejecting the whole filter. Adapt the operator vocabulary to your host's grammar. Omit the in-source `as SafeSqlFragment` casts on operators only if your type system can prove the operator set closed.
