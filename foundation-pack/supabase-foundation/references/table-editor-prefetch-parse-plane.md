<!-- capsule-v2 -->
# Table-editor prefetch + parse plane — how do you prefetch a table editor page and keep grid state consistent across URL, localStorage, and react-query?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** A table editor page needs the entity definition AND its first rows before paint, plus per-table grid state (sorts/filters/columns) that survives navigation and reloads — how do the prefetch chain, the Entity→grid projection, and the persistence layer stay mutually consistent?

## Entity union + type guards gate every projection (`data/table-editor/table-editor-types.ts`)
**Path/Symbol:** `apps/studio/data/table-editor/table-editor-types.ts` : `Entity` union (:55), `isTableLike` (:71-73), `isMsSqlForeignTable` (:79-81); `WRAPPER_HANDLERS.MSSQL = 'mssql_fdw_handler'` (`components/interfaces/Integrations/Wrappers/Wrappers.constants.ts` :15).
**Signature:** `isMsSqlForeignTable(entity?: Entity): entity is ForeignTable`.
**Data Shape:** `Entity = Table | PartitionedTable | View | MaterializedView | ForeignTable`, discriminated by `entity_type`. Table-like-only fields (primary_keys, unique_indexes, relationships, live_rows_estimate) exist ONLY on Table/PartitionedTable — the doc comment on isTableLike: "Foreign tables are not considered table-like." The MS-SQL guard is foreign-table ∧ handler-name equality against the fdw handler constant.

### Decisive source
```ts
export function isMsSqlForeignTable(entity?: Entity): entity is ForeignTable {
  return isForeignTable(entity) && entity.foreign_data_wrapper_handler === WRAPPER_HANDLERS.MSSQL
}
```

**Flow:** every consumer (parseSupaTable, row-count, MS-SQL sort exclusion, validation banners) branches through these guards instead of duck-typing field presence.
**Invariant:** a discriminated union over catalog entity kinds must carry its kind-specific fields ONLY on the right members, and every cross-cutting behavior (row counts, sorts, masking) must branch through a named guard — the MS-SQL case shows why: one remote planner behaves differently, and the check must be a single constant-comparison, not a string sniff.
**Probe:** direct read at the pin; guard exercised indirectly by the URL-param test suite below; no dedicated types test — recorded absence.

## Entity→grid projection with table-like defaults (`components/grid/SupabaseGrid.utils.ts`)
**Path/Symbol:** `apps/studio/components/grid/SupabaseGrid.utils.ts` : `parseSupaTable` (:84-146), `formatSortURLParams` (:27-49), `formatFilterURLParams` (:51-79).
**Signature:** `parseSupaTable(table: Entity): SupaTable`.
**Data Shape:** table-like-only fields default to empty/0 for views/matviews/foreign tables via isTableLike gates (`estimateRowCount: isTableLike(table) ? table.live_rows_estimate : 0`); FK relationship matched per column by the triple `(source_schema, source_table_name, source_column_name)`; `primaryKey` = names of primary_keys or undefined. URL grammar: sort `column:order` REJECTED if the column is not present in `table.columns` ("reject any possible malformed sort param ... to avoid confusion"); filter `column:abbrev:value` with the value rejoined on ':' (colon-in-value support); malformed entries dropped, never thrown.

### Decisive source
```ts
const supaColumns: SupaColumn[] = columns.map((column) => {
  const temp = {
    position: column.ordinal_position,
    name: column.name,
    defaultValue: column.default_value as string | null | undefined,
    dataType: column.data_type,
    format: column.format,
    isPrimaryKey: false,
    ...
  }
  const primaryKey = primaryKeys.find((pk) => pk.name == column.name)
  temp.isPrimaryKey = !!primaryKey

  const relationship = relationships.find((relation) => {
    return (
      relation.source_schema === column.schema &&
      relation.source_table_name === column.table &&
      relation.source_column_name === column.name
    )
  })
```

**Flow:** getTableEditor (below) returns an Entity → parseSupaTable projects it to the grid shape ONCE; both the state creator and the row/count queries call the same projection so grid columns, keyset eligibility, and filter formatting all see identical metadata.
**Invariant:** one projection function is the single translation point between the wire/catalog shape and the UI shape; URL-originated sort/filter params are validated AGAINST the actual table columns before use (unknown column ⇒ drop the param, don't error the page).
**Probe:** direct read at the pin; `useTableEditorFiltersSort.test.ts` (read whole) pins the URL-param parsing hook (old+new syntax, empty cases); parseSupaTable itself has no dedicated test — recorded absence. Vitest unexecutable in-lane — never claimed passing.

## Prefetch chain: entity first, locally-saved state as fallback, errors eaten (`data/prefetchers/project.$ref.editor.$id.tsx`)
**Path/Symbol:** `apps/studio/data/prefetchers/project.$ref.editor.$id.tsx` : `prefetchEditorTablePage` (:36-70), `usePrefetchEditorTablePage` (:73-113, error swallow :101); `data/table-editor/table-editor-query.ts` : `PG_META_SCOPED_INTROSPECTION_FLAG` (:10), `getTableEditor` (:22-42), `prefetchTableEditor` (:67-70), `tableEditorQueryOptions` (:74-84).
**Signature:** `prefetchEditorTablePage({ queryClient, projectRef, connectionString, readReplicaIdentifier, id, sorts?, filters?, roleImpersonationState?, scoped? }): Promise<void>`.
**Data Shape:** prefetchTableEditor runs `getTableEditorSql({ id, scoped })` through executeSql and projects `result[0]?.entity ?? null`; its queryKey appends `{ scoped: !!scoped }` so scoped and legacy introspection results NEVER share a cache slot (the flag name is exported once here and shared by editor/rows/count queries). The page prefetch then reads locally-saved sorts/filters and uses them as FALLBACKS only: `sorts ?? formatSortURLParams(entity, localSorts)` — explicit params win, saved state fills the gap; then prefetchTableRows page 1 at TABLE_EDITOR_DEFAULT_ROWS_PER_PAGE. The hook version swallows all prefetch errors: "eat prefetching errors as they are not critical" — prefetch is best-effort; the real fetch re-runs on navigation.

### Decisive source
```ts
return prefetchTableEditor(queryClient, {
  projectRef,
  connectionString,
  id,
  scoped,
}).then((entity) => {
  if (entity) {
    const { sorts: localSorts = [], filters: localFilters = [] } =
      loadTableEditorStateFromLocalStorage(projectRef, entity.id) ?? {}

    prefetchTableRows(queryClient, {
      projectRef,
      connectionString,
      readReplicaIdentifier,
      tableId: id,
      sorts: sorts ?? formatSortURLParams(entity, localSorts),
      filters: filters ?? formatFilterURLParams(localFilters),
      page: 1,
      limit: TABLE_EDITOR_DEFAULT_ROWS_PER_PAGE,
      roleImpersonationState,
      scoped,
    })
  }
})
```

**Flow:** link hover → router.prefetch(code) + data prefetch chain (entity → saved-state fallback → rows page 1) → all into the react-query cache under the same keys the page's real hooks use, so navigation renders from cache.
**Invariant:** a prefetch chain must (a) order dependencies (rows need the entity for column validation), (b) treat persisted user state as a FALLBACK behind explicit params, and (c) be fail-silent — a failed prefetch degrades to a slower page, never to a broken one, because the authoritative fetch repeats the same work under the same cache keys.
**Probe:** direct read at the pin; no dedicated prefetch test — recorded absence.

## Grid-state persistence: session-over-local read, write-to-both, partial merge (`components/grid/SupabaseGrid.utils.ts`)
**Path/Symbol:** same file : `loadTableEditorStateFromLocalStorage` (:152-160), `saveTableEditorStateToLocalStorage` (:194-230), `saveTableEditorStateToLocalStorageDebounced` (:232-235).
**Signature:** `saveTableEditorStateToLocalStorage({ projectRef, tableId, gridColumns?, sorts?, filters?, sensitiveDataColumns? }): void`.
**Data Shape:** storage key `${prefix}_${projectRef}`; the JSON is keyed by tableId. READ prefers sessionStorage over localStorage ("Prefer sessionStorage (scoped to current tab) over localStorage"); WRITE goes to BOTH ("so it's consistent to current tab"). Per-tableId merge `{ ...previousConfig, ...config }` where config OMITS undefined fields — saving sorts must not clobber saved gridColumns (partial-update semantics). Empty-string sorts/filters are filtered out before save. 500ms debounce wrapper.

### Decisive source
```ts
const config = {
  ...(gridColumns !== undefined && { gridColumns }),
  ...(sorts !== undefined && { sorts: sorts.filter((sort) => sort !== '') }),
  ...(filters !== undefined && { filters: filters.filter((filter) => filter !== '') }),
  ...(sensitiveDataColumns !== undefined && { sensitiveDataColumns }),
}

let savedJson
if (savedStr) {
  savedJson = JSON.parse(savedStr)
  const previousConfig = savedJson[tableId]
  savedJson = { ...savedJson, [tableId]: { ...previousConfig, ...config } }
} else {
  savedJson = { [tableId]: config }
}
// Save to both localStorage and sessionStorage so it's consistent to current tab
safeLocalStorage.setItem(storageKey, JSON.stringify(savedJson))
safeSessionStorage.setItem(storageKey, JSON.stringify(savedJson))
```

**Flow:** multiple independent writers (URL sync effect, valtio state subscription, explicit saves) hit the same key; the undefined-omission + spread-merge makes concurrent partial writes composable without a lock.
**Invariant:** a multi-writer persisted state blob needs (a) asymmetric read/write storage tiers (tab-scoped wins on read, both written on save), (b) field-level partial-update semantics via undefined omission — never a full-blob overwrite from a writer that only owns some fields, and (c) debouncing because the writers fire on every keystroke-level state change.
**Probe:** direct read at the pin; no dedicated persistence test — recorded absence.

## MS-SQL foreign-table sort exclusion (the pass-3 named edge case, mined) (`data/table-rows/table-rows-query.ts`)
**Path/Symbol:** `apps/studio/data/table-rows/table-rows-query.ts` : equality-column collection (:353-355), exclusion (:357-363), `sortExcludedColumns` hand-off (:372).
**Signature:** internal to `getTableRows`.
**Data Shape:** equality-filter columns (`=` or `is`) are collected; for MS-SQL foreign tables ONLY they are passed as `sortExcludedColumns` into getTableRowsSql (pass-3's cursor-pagination capsule covers the rest of the ordering ladder).

### Decisive source
```ts
// There is an edge case for MS SQL foreign tables, where the Postgres query
// planner may drop sorts that are redundant with filters, resulting in
// invalid MS SQL syntax. To prevent this, we exclude potentially conflicting
// columns from potential default sort columns.
const excludedColumns = isMsSqlForeignTable(entity)
  ? Array.from(new Set(equalityFilterColumns))
  : undefined
```

**Flow:** default-sort candidate selection (primary key / unique index / sortable columns) now receives the set of columns whose ORDER BY the remote planner might legally drop; candidates overlapping it are skipped.
**Invariant:** when the executing planner is NOT the one your SQL assumes (foreign data wrappers), planner optimizations like redundant-sort elimination can turn valid Postgres into invalid remote SQL — default-sort selection must therefore know about active equality filters, gated on the specific remote engine, not applied globally.
**Probe:** direct read at the pin; no dedicated test for this branch — recorded absence (the surrounding getTableRowsSql ordering is pinned by table-rows-query.test.ts, pass 3).

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "prefetchEditorTablePage parseSupaTable isMsSqlForeignTable saveTableEditorStateToLocalStorage formatSortURLParams", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: the entity-first prefetch chain with fail-silent error swallowing and same-cache-key repeat; persisted-user-state-as-fallback behind explicit params; the single Entity→UI projection with kind-gated defaults; discriminated-union type guards as the only branching point for engine-specific behavior; session-over-local read / write-to-both persistence with undefined-omission partial merges and debouncing; URL-param validation against actual table columns with silent drop; remote-planner sort-exclusion gated on the specific fdw handler. Adapt storage keys, debounce window, and the entity union to your catalog. Omit Supabase-product specifics: the exact fdw handler constant, platform connection strings, and the react-query wiring. Direct-test caveat: useTableEditorFiltersSort.test.ts read whole; no dedicated tests for parseSupaTable/prefetch/persistence (recorded absences); vitest unexecutable in-lane — never claimed passing.
