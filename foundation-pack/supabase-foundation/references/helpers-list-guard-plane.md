<!-- capsule-v2 -->
# list-guard helper plane — how do IN-clauses, row aggregation, and identifier lookups avoid empty/degenerate SQL?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** How does shared SQL-fragment plumbing prevent bare `IN ()`, non-deterministic aggregates, and ambiguous identifier lookups?

## Shared fragment helpers
**Path/Symbol:** `packages/pg-meta/src/helpers.ts` : `filterByList` (:24-34), `coalesceRowsToArray` (:3-22), `exceptionIdentifierNotFound` (:36-38); consumer pattern `packages/pg-meta/src/pg-meta-tables.ts` : `getIdentifierWhereClause` (:67-75).
**Signature:** `function filterByList(include?: string[], exclude?: string[], defaultExclude?: string[]): SafeSqlFragment`; `coalesceRowsToArray(source: string, filter: SafeSqlFragment, orderBy?: SafeSqlFragment): SafeSqlFragment`.
**Data Shape:** include/exclude are plain string lists (schema or entity names); the function owns escaping via `literal()` per element.

### Decisive source
```ts
export function filterByList(include?: string[], exclude?: string[], defaultExclude?: string[]) {
  if (defaultExclude) {
    exclude = defaultExclude.concat(exclude ?? [])
  }
  if (include?.length) {
    return safeSql`IN (${joinSqlFragments(include.map(literal), ',')})`
  } else if (exclude?.length) {
    return safeSql`NOT IN (${joinSqlFragments(exclude.map(literal), ',')})`
  }
  return safeSql``
}
```
```ts
// pg-meta-tables.ts — repeated across triggers/columns/publications/views/roles
function getIdentifierWhereClause(identifier: TableIdentifier): SafeSqlFragment {
  if ('id' in identifier && identifier.id) {
    return safeSql`${ident('id')} = ${literal(identifier.id)}`
  }
  if ('name' in identifier && identifier.name && identifier.schema) {
    return safeSql`${ident('name')} = ${literal(identifier.name)} and ${ident('schema')} = ${literal(identifier.schema)}`
  }
  throw new Error('Must provide either id or name and schema')
}
```

**Flow:** include non-empty → `IN ('a','b')` wins outright · else exclude non-empty → `NOT IN (...)` · else EMPTY fragment (no clause at all — never `IN ()`, which is a syntax error / always-false predicate) · `defaultExclude` silently merges caller-supplied system-schema exclusions ahead of user ones. `coalesceRowsToArray` wraps `array_agg(row_to_json(x)) FILTER (WHERE ...)` in `COALESCE(..., '{}')` so zero rows render as an empty array, with an optional inner `ORDER BY` making output deterministic; omitting it preserves historical plan-order bytes for existing callers.
**Invariant:** include-beats-exclude precedence is semantic: when a caller asks for specific schemas, excludes must not narrow them further. The identifier trichotomy (id | name+schema | throw) is fail-loud — no silent fallback to a full-table scan.
**Probe:** no dedicated unit test for helpers.ts (coverage caveat); decisive anchors verified by direct read: `helpers.ts:29/31` literal-mapped joins, `pg-meta-tables.ts:74` throw arm. Consumer usage visible in `pg-meta-tables.ts:list` :97-99 (`filterByList(includedSchemas, excludedSchemas)` feeding the tables CTE).
**Retrieve:** executed live this pass:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "safeSql untrustedSql acceptUntrustedSql branded sql format escape", limit: 40 })
// trace_path(safeSql, inbound, depth 1) page 1 lists helpers.filterByList / coalesceRowsToArray / exceptionIdentifierNotFound as direct callers; callers_total 219
```

## Verdict
Adopt the tri-state include/exclude/no-op clause builder and the COALESCE-empty-array wrapper — both eliminate whole bug classes in dashboard listing endpoints. Adapt `defaultExclude` to your host's system-schema set. Omit the orderBy compat parameter only if you have no historical byte-stability to preserve.
