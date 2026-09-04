<!-- capsule-v2 -->
# pg-meta entity retrieve + scoped-OID plane — how do you look up one catalog relation without computing enrichment for the entire catalog?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What identifier-resolution pattern do pg-meta's entity modules share, and how does the tables retrieve path push a single OID into its enrichment CTEs so a hundreds-of-schemas database stops timing out at ~58s?

## Identifier trichotomy across entity modules (`packages/pg-meta/src`)
**Path/Symbol:** `packages/pg-meta/src/pg-meta-tables.ts` : `TableIdentifier` (:65), `getIdentifierWhereClause` (:67-75); same shape in `pg-meta-views.ts` (:72-81), `pg-meta-columns.ts` (:91-101), `pg-meta-triggers.ts` (:15-25), `pg-meta-publications.ts` (:51-60).
**Signature:** `type XIdentifier = Pick<PX, 'id'> | Pick<PX, 'name' | 'schema' [...]>`; `function getIdentifierWhereClause(identifier): SafeSqlFragment`.
**Data Shape:** every module resolves an entity by EITHER its numeric `id` OR a name-based key whose ARITY varies per entity: tables/views = name+schema; columns/triggers = name+schema+table; publications = name alone. Both branches emit through the pass-2 escaping ladders (`ident('id') = literal(id)` / `ident('name') = literal(name) and ...`); anything else throws a module-specific message ('Must provide either id or name and schema' / '... id or schema, name and table' / '... id or name'). The clause is then inlined into a CTE-wrapped SELECT (`with tables as (...) select * from tables where ${clause};`).

### Decisive source
```ts
type TableIdentifier = Pick<PGTable, 'id'> | Pick<PGTable, 'name' | 'schema'>

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

**Flow:** each entity module exposes `list()` (filterByList schema include/exclude + limit/offset — pass-2's helpers capsule) and `retrieve(identifier)`; the trichotomy is the shared resolution kernel, repeated per module with that module's key arity rather than generalized into one parameterized helper.
**Invariant:** fail-loud on partial identifiers — a name without its schema/table scope is ambiguous in Postgres and must throw at SQL-build time, not return a wrong row. The union type makes the arity a compile-time contract per entity.
**Probe:** direct read of all five modules at the pin; the DB-backed suites under `packages/pg-meta/test/` (tables/views/columns/triggers/publications .test.ts) exercise both branches but require live Postgres — standing runner block, never claimed passing.

## Scoped OID pushdown (`pg-meta-tables.ts` retrieve + `src/sql/tables.ts`)
**Path/Symbol:** `packages/pg-meta/src/pg-meta-tables.ts` : `retrieve` (:118-165, scoped branch :131-158); `packages/pg-meta/src/sql/tables.ts` : `getTablesSql(targetOid?)` (:23-141), frozen `TABLES_SQL` (:143-147); `src/sql/columns.ts` : `getColumnsSql({ filter })` (:21-24).
**Signature:** `retrieve(identifier: TableIdentifier & { scoped?: boolean }): { sql: SafeSqlFragment; zod }`.
**Data Shape:** when `identifier.scoped`, the target OID is resolved ONCE as a scalar fragment — a plain literal for the id branch, or an uncorrelated scalar subquery via pg_class's (relname, relnamespace) index for the name+schema branch — and pushed into BOTH enrichment CTEs: `getTablesSql(targetOid)` injects `AND c.oid = ${targetOid}` into the main pg_class scan, the primary-key subquery, and the relationships subquery as `(c.conrelid = ${oid} OR c.confrelid = ${oid})` (BOTH FK directions, matching what the unscoped query would have matched by name); `getColumnsSql({ filter: { column: 'oid', predicate: safeSql`= ${targetOid}` } })` scopes the columns CTE. The in-source rationale: the legacy unscoped form computes sizes/PKs/relationships for the ENTIRE catalog and timed out at ~58s on a hundreds-of-schemas database; a multiply-referenced CTE would be materialized and act as an optimization barrier forcing seq scans — hence a scalar the planner evaluates once as an initplan constant driving INDEX scans.

### Decisive source
```ts
// Resolve the target OID as a scalar the planner evaluates once (initplan):
// a literal for the id branch, or an uncorrelated scalar subquery resolving
// via pg_class's (relname, relnamespace) index for the name+schema branch.
let targetOid: SafeSqlFragment
if ('id' in identifier && identifier.id) {
  targetOid = safeSql`${literal(identifier.id)}`
} else if ('name' in identifier && identifier.name && identifier.schema) {
  targetOid = safeSql`(select tc.oid from pg_class tc join pg_namespace tn on tn.oid = tc.relnamespace where tc.relname = ${literal(identifier.name)} and tn.nspname = ${literal(identifier.schema)})`
} else {
  throw new Error('Must provide either id or name and schema')
}
const scopedTables = getTablesSql(targetOid)
const scopedColumns = getColumnsSql({
  filter: { column: 'oid', predicate: safeSql`= ${targetOid}` },
})
```

**Flow:** scoped branch renders `with tables as (getTablesSql(oid)), columns as (getColumnsSql(oid-filter)) select *, coalesceRowsToArray(columns, join, ordinal_position) from tables where <trichotomy clause>` — note the outer WHERE is KEPT even though the CTEs are already scoped (output rows identical to legacy; the outer filter already restricted to this relation). The scoped path also adds a deterministic relationships ORDER BY (constraint_name, source_column_name, target_column_name) because legacy order is plan-dependent; a composite FK expands to one entry per source×target column pair sharing constraint_name, so the column names tie-break.
**Invariant:** push the restriction into EVERY enrichment subquery, not just the outer WHERE — the cost lives in the subqueries (sizes, PK aggregation, FK joins), so an outer filter alone still computes the whole catalog. The scalar-not-CTE choice is load-bearing: a CTE referenced multiple times gets materialized and becomes an optimization barrier. Output equivalence between scoped and unscoped forms must be enforced by EXECUTION-based tests, not byte-for-byte SQL snapshots (the two render differently by design).
**Probe:** `packages/pg-meta/test/tables.test.ts` :40-102 (DB-backed, read whole; requires live Postgres — standing runner block, never claimed passing) pins scoped-vs-legacy row equality for parent-by-id, child-by-name+schema, child-by-id covering incoming FK, outgoing FK, self-referential FK, enum, comment — with legacy relationships canonicalized to the scoped ORDER BY before comparison.

## Frozen legacy twin + feature flag
**Path/Symbol:** `src/sql/tables.ts` : `TABLES_SQL` comment (:142-145); flag references across `src/sql/studio/database/rows.ts` (:101, :157), `get-count-estimate.ts` (:15), `table-definition.ts` (:27), `table-editor/table.ts` (:348), `types.ts` (:13), `table-privileges.ts` (:4), `column-privileges.ts` (:6).
**Signature:** `export const TABLES_SQL = getTablesSql()` — the unscoped rendering, exported verbatim.
**Data Shape:** while the `pgMetaScopedIntrospection` flag is off, production serves the FROZEN legacy rendering; the in-source instruction is "Do not edit its shape — it must keep matching production behavior until the flag cleanup deletes it." The same frozen-twin pattern recurs across the studio SQL builders (rows, count-estimate, table-definition, table-editor, types, privileges).

### Decisive source
```ts
// FROZEN legacy path: the unscoped rendering served while the
// pgMetaScopedIntrospection flag is off. Do not edit its shape -- it must keep
// matching production behavior until the flag cleanup deletes it. The scoped
// form is getTablesSql(targetOid) (used by tables.retrieve).
export const TABLES_SQL = getTablesSql()
```

**Flow:** new behavior ships behind a flag with BOTH renderings coexisting; the legacy constant is generated FROM the same builder (empty-scope fragments) so it cannot drift structurally, and is marked frozen against hand edits.
**Invariant:** a performance rewrite of a catalog query is only safe to ship when the old form stays byte-stable for rollback/flag-off traffic AND equivalence is pinned by execution tests — the frozen-twin + flag + execution-equivalence trio is the porting unit, not any single piece.
**Probe:** direct read at the pin; grep confirms the frozen-path comment family spans eight studio SQL files.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads plus the direct test at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "getTablesSql targetOid getIdentifierWhereClause scoped retrieve", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the per-entity identifier trichotomy (id | full name-key | fail-loud, arity as a compile-time union type); the scoped-OID pushdown (resolve the target once as a scalar — literal or uncorrelated index-backed subquery — and inject it into every enrichment subquery, keeping the outer WHERE too); scoped-only deterministic ordering where legacy order is plan-dependent; and the frozen-legacy-twin + feature-flag + execution-equivalence-test trio for shipping the rewrite. Adapt the OID resolution to your catalog's natural key index. Omit nothing structural: pushing the filter only to the outer WHERE is the classic mistake this capsule exists to prevent — the cost is in the subqueries.
