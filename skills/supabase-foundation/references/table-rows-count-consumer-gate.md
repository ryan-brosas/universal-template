<!-- capsule-v2 -->
# Table-rows count consumer gate — how do you consume an exact-vs-estimate row count without caching transient permission state?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** The SQL side (pg-meta-rows-count-scoped-gate capsule) decides exact-count vs estimate based on a read-only-context flag — but that flag depends on an ASYNC permission check that starts out false. How does the consumer avoid firing the query with a transient degraded flag and poisoning the cache?

## The consumer chain: entity prefetch → projection → impersonation-wrapped count SQL (`data/table-rows/table-rows-count-query.ts`)
**Path/Symbol:** `apps/studio/data/table-rows/table-rows-count-query.ts` : `getTableRowsCount` (:44-97); `data/table-rows/utils.ts` : `formatFilterValue` (:9-25).
**Signature:** `getTableRowsCount({ queryClient, projectRef, connectionString, tableId, filters?, roleImpersonationState?, enforceExactCount?, isReadOnlyContext = false, scoped }, signal?): Promise<{ count?: number, is_estimate?: boolean }>`.
**Data Shape:** prefetchTableEditor FIRST (throw `'Table not found'` if missing — the count query cannot run without the entity's column metadata) → parseSupaTable (pass-6 table-editor-prefetch-parse-plane) → per-filter `formatFilterValue` (numeric columns: value coerced to number UNLESS NaN or |v| > MAX_SAFE_INTEGER — keeps huge numeric ids as strings) → `wrapWithRoleImpersonation(getTableRowsCountSql({ table, filters, enforceExactCount, isReadOnlyContext, scoped }), roleImpersonationState)` → executeSql carrying `isRoleImpersonationEnabled` → project `{ count: result?.[0]?.count, is_estimate: result?.[0]?.is_estimate ?? false }`.

### Decisive source
```ts
const entity = await prefetchTableEditor(queryClient, {
  projectRef,
  connectionString,
  id: tableId,
  scoped,
})
if (!entity) {
  throw new Error('Table not found')
}

const table = parseSupaTable(entity)

const formattedFilters = filters?.map((x) => ({ ...x, value: formatFilterValue(table, x) }))
const sql = wrapWithRoleImpersonation(
  getTableRowsCountSql({
    table,
    filters: formattedFilters,
    enforceExactCount,
    isReadOnlyContext,
    scoped,
  }),
  roleImpersonationState
)
```

**Flow:** this is the studio-side half of pass-5's rows-count scoped gate: the SQL builder receives `isReadOnlyContext` and `scoped`, and the consumer here decides both — `scoped` from the shared `pgMetaScopedIntrospection` flag (exported by table-editor-query.ts), `isReadOnlyContext` from connection type + permissions.
**Invariant:** a query whose SQL SHAPE depends on caller capabilities must resolve those capabilities at the consumer and thread them into BOTH the SQL builder and the cache key — otherwise two users with different permissions share one cache slot with one user's SQL shape.
**Probe:** direct read at the pin; no dedicated test for getTableRowsCount — recorded absence (the SQL side is pinned by DB-backed rows-count.test.ts under the standing runner block). `data/table-rows/utils.test.ts` (59L, read whole this pass) directly pins `formatFilterValue`: non-numerical passthrough, in-range numeric coercion (incl. negatives), invalid-number string passthrough, and the large ±bigint-as-string regression (the previous implementation guarded only the upper bound, so large NEGATIVE bigints were silently rounded). Vitest unexecutable in-lane — read whole, never claimed passing.

## The permission-settle enable gate (`data/table-rows/table-rows-count-query.ts`)
**Path/Symbol:** same file : `useTableRowsCountQuery` (:98-156), `isReadOnlyContext` derivation (:135), settle gate (:146-153).
**Signature:** `useTableRowsCountQuery({ projectRef, tableId, ...args }, { enabled, ...options })`.
**Data Shape:** `isReadOnlyContext = type === 'replica' || !canSQLAdminWrite` — replica is known synchronously from the connection string source, but `canSQLAdminWrite` comes from an async permission check that STARTS OUT FALSE while loading. The queryKey includes `scoped` (and readReplicaIdentifier) so degraded/scoped variants never share slots.

### Decisive source
```ts
enabled:
  enabled &&
  typeof projectRef !== 'undefined' &&
  typeof tableId !== 'undefined' &&
  (!IS_PLATFORM || typeof connectionString !== 'undefined') &&
  // isReadOnlyContext resolves to `type === 'replica' || !canSQLAdminWrite`: for
  // read replicas it's already known synchronously, but otherwise it depends on
  // canSQLAdminWrite, which starts out `false` while permissions are loading.
  // Firing while that's still in flight would cache a transient
  // isReadOnlyContext:true (and, on a never-analyzed table, a scoped
  // count:-1/is_estimate:true) for what may actually be a writable user. Wait
  // for the permission check to settle before firing in that case.
  (type === 'replica' || !isPermissionsLoading),
```

**Flow:** replica path fires immediately (known synchronously); primary-path waits for `isPermissionsLoading` to clear before the first fetch; once fired, the result caches under the capability-inclusive key.
**Invariant:** when a query's inputs depend on an async capability check whose LOADING state equals its NEGATIVE value (false while unknown), the enable condition must distinguish "known false" from "still loading" — `(syncKnown || !isLoading)` — or the first fetch runs with a transient degraded input and the cache stores the degraded result for a user who may actually be capable. This is the consumer-side twin of any "degrade under missing capability" SQL gate: the gate is only as honest as the moment you choose to fire.
**Probe:** direct read at the pin; no dedicated test for the hook's enable gate — recorded absence.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "getTableRowsCount isReadOnlyContext isPermissionsLoading canSQLAdminWrite formatFilterValue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the entity-first consumer chain (metadata prefetch → single projection → filter-value coercion with safe-integer guard → capability-flagged SQL build → impersonation wrap); threading async-resolved capabilities into BOTH the SQL builder and the cache key; and the `(syncKnown || !isLoading)` enable gate that refuses to fire while a false-defaulting permission check is still loading. Adapt the permission action, the degradation sentinel, and the key members to your stack. Omit Supabase-product specifics: the platform IS_PLATFORM branch, the exact permission action constant, and pg-meta endpoint paths. Direct-test caveat: utils.test.ts (59L) read whole pins formatFilterValue; no dedicated tests exist for getTableRowsCount or the hook gate (recorded absences); vitest unexecutable in-lane — never claimed passing.
