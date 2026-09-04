<!-- capsule-v2 -->
# Query-cell source rebrand plane — how does a query cell's SQL body keep its taint brand correlated with its backend tag across wire round-trips and backend switches?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** A notebook cell can run against Postgres or the logs engine; its SQL text is untrusted until a Run gesture. Where exactly is the plain wire string turned into a dialect-branded fragment, what happens to the body when the user switches backends, and how does the closed source registry stay safe to extend?

## Closed source registry (`data/query-sources/query-source-registry.ts`)
**Path/Symbol:** `apps/studio/data/query-sources/query-source-registry.ts` : `QUERY_SOURCE_REGISTRY` (:60-71), `querySourceBindingSchema` (:49-53), `cloneTimeRange` (:83-86), `createDefaultSourceBinding` (:88-101), `toQuerySourceBinding` (:128-134), `getQuerySourceBinding` (:141-153).
**Signature:** `createDefaultSourceBinding(tag: 'database' | 'logs'): QuerySourceBinding`; `toQuerySourceBinding(value: SourceTagged<...>): DatabaseBinding | LogsBinding | QuerySourceBinding` (overloaded so a narrowed carrier gets a narrowed binding back).
**Data Shape:** the tag set is a CLOSED set by design — in-source comment: each tag is a distinct SQL dialect with its own escaping rules, wire boundary, and safe-SQL brand, so "picking the wrong one is a security bug rather than a configuration error". The registry enumerates only what is downstream of that choice: endpoints, labels, default parameters. Parameter shapes live in the notebook wire schema (one definition shared with the API and agent tool surface); this module borrows them. Bindings are flat `{_tag, ...parameters}` — carriers store fields inline, not under a `source` key.

### Decisive source
```ts
/** Defensive copy so a valtio-proxied range never leaks into a freshly built binding. */
const cloneTimeRange = (range: Readonly<TimeRange>): TimeRange =>
  range._tag === 'relative_time_range'
    ? { _tag: range._tag, unit: range.unit, amount: range.amount }
    : { _tag: range._tag, start: range.start, end: range.end }

export function createDefaultSourceBinding(tag: QuerySourceTag): QuerySourceBinding {
  if (tag === 'logs') {
    return {
      _tag: 'logs',
      time_range: cloneTimeRange(QUERY_SOURCE_REGISTRY.logs.parameters.time_range),
    }
  }
  return { _tag: 'database' }
}
```

**Flow:** UI reads available sources from `QUERY_SOURCES` → builds bindings through `createDefaultSourceBinding`/projections → every projection CLONES nested parameter objects (time ranges) so a reactive-store proxy never aliases into a freshly built value → zod `discriminatedUnion('_tag', [...].strict())` validates at the wire boundary, rejecting cross-tag parameters.
**Invariant:** defaults are deep-copied per call — two `createDefaultSourceBinding('logs')` results must not share a `time_range` object, or editing one silently mutates the other's store-backed source. Cross-tag parameters must fail validation (strict objects), not be silently dropped.
**Probe:** `apps/studio/data/query-sources/query-source-registry.test.ts` (pure vitest, read whole; unexecutable in-lane — standing block) pins: both endpoints registered; `first.time_range).not.toBe(second.time_range)` for independent defaults; cross-tag parameter rejection (logs+database_identifier, database+time_range, bad time unit all throw); projection copy semantics (`binding.time_range).not.toBe(time_range)`).

## Wire/domain brand transform (`data/content/notebooks/notebook-schema.ts`)
**Path/Symbol:** `apps/studio/data/content/notebooks/notebook-schema.ts` : `cellDomainSchema` transform (:195-208), `toWireCell` (:218-231), `timeRangeSchema` (:40-55), `databaseSourceSchema` (:57-63), `logsSourceSchema` (:65-67).
**Signature:** domain parse: wire cell with `sql: z.string()` → domain cell with `unchecked_sql: UntrustedSqlFragment | UntrustedLogSqlFragment`; `toWireCell(cell): CellWire` strips the brand back to a plain string.
**Data Shape:** the brand is chosen by CELL TAG at the single transform site: `database_cell` ⇒ pg-meta's `untrustedSql`, `log_cell` ⇒ the logs family's `untrustedLogSql` (pass-3's disjoint brands). `view` defaults to `'table'` at the same site. The absolute time range carries an ordering refine that stays quiet when a bound is already unparseable ("an unparseable bound is already reported against its own field; the ordering rule stays quiet so it doesn't add a second, misleading issue").

### Decisive source
```ts
// The domain shape: parses the wire cell (`cellSchema`), transforms `sql` into a branded
// `unchecked_sql`, and defaults `view` to 'table'.
const cellDomainSchema = cellSchema.transform((cell) => {
  switch (cell._tag) {
    case 'database_cell': {
      const { sql, view, ...rest } = cell
      return { ...rest, view: view ?? 'table', unchecked_sql: untrustedSql(sql) }
    }
    case 'log_cell': {
      const { sql, view, ...rest } = cell
      return { ...rest, view: view ?? 'table', unchecked_sql: untrustedLogSql(sql) }
    }
  }
})
```

**Flow:** saved notebook arrives as wire JSON (plain `sql`) → domain transform brands by tag → every in-memory mutation keeps the brand (below) → `toWireCell` debrands on save. The brand therefore exists ONLY inside the domain lifetime — persistence is always plain text, re-branded on every load.
**Invariant:** branding happens at exactly one boundary (the schema transform) and debranding at exactly one (the wire serializer). Any code path that stores or sends `unchecked_sql` without going through `toWireCell` leaks a branded string where a plain string is expected; any path that rebrands ad hoc drifts from the cell's tag.
**Probe:** no dedicated upstream test for the transform itself; confirmed by direct read of both directions at the pin plus the consumer tests below exercising branded cells end-to-end.

## Backend-switch + mutation helpers (`components/interfaces/Explorer/QueryCell/QueryCell.utils.ts`)
**Path/Symbol:** `apps/studio/components/interfaces/Explorer/QueryCell/QueryCell.utils.ts` : `DEFAULT_CELL_ROW_LIMIT` (:14), `cloneChartConfig` (:24-26), `changeCellSource` (:73-92), `setCellSql` (:99-118), `setCellRowLimit` (:124-134), `toQueryModel` (:141-151).
**Signature:** `changeCellSource(cell: Snapshot<QueryCell>, source: QuerySourceBinding): QueryCell`; `toQueryModel(cell, sql: string): ExplorerQueryModel`.
**Data Shape:** valtio snapshots are deep-readonly, so writable copies rebuild only the array that needs it (`chart.y_series`). `changeCellSource` carries the query text across backends UNCHANGED but rebrands it for the new dialect; moving logs→database restores `row_limit` to `DEFAULT_CELL_ROW_LIMIT` (100) because log cells have no row-limit concept; chart config survives via `cloneChartConfig`. The in-source NOTE documents the known-bad default: carrying Postgres text into a logs cell "asserts a dialect the text was never written in" and will almost always fail to run — kept because it is least-destructive and needs no confirmation prompt, pending product data on whether users switch to port queries or start fresh.

### Decisive source
```ts
export function changeCellSource(cell: Snapshot<QueryCell>, source: QuerySourceBinding): QueryCell {
  const base = copyQueryCellBase(cell)
  if (source._tag === 'logs') {
    return { ...base, _tag: 'log_cell', unchecked_sql: untrustedLogSql(cell.unchecked_sql), time_range: source.time_range }
  }
  return {
    ...base,
    _tag: 'database_cell',
    unchecked_sql: untrustedSql(cell.unchecked_sql),
    row_limit: cell._tag === 'database_cell' ? cell.row_limit : DEFAULT_CELL_ROW_LIMIT,
    database_identifier: source.database_identifier,
  }
}
```

**Flow:** source menu emits a binding → `changeCellSource` retags the cell, rebrands the body for the new dialect, swaps backend-specific fields (time_range vs row_limit/database_identifier) → editor buffer writes go through `setCellSql` which rebrands by the cell's CURRENT tag → `toQueryModel` decides the buffer's brand by cell tag "so the dialect can't drift from the cell it belongs to".
**Invariant:** the brand always follows the cell tag, decided in ONE narrowing per helper — never re-derived at call sites. Backend-specific fields must be swapped, not merged: a database cell must not carry a time_range, a log cell must not carry a row_limit.
**Probe:** `apps/studio/components/interfaces/Explorer/QueryCell/QueryCell.utils.test.ts` (pure vitest, read whole; unexecutable in-lane — standing block) pins: carry-over both directions with exact field sets; default row-limit restore on logs→database; selected database applied on move; chart preserved across backend change AND not aliased (`next.chart).not.toBe(DATABASE_CELL.chart)`); `setCellRowLimit` passes log cells through unchanged; `toQueryModel` tags each cell type with its own fields.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct whole-file reads of all three files plus their two direct tests at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "changeCellSource getQuerySourceBinding createDefaultSourceBinding cellDomainSchema unchecked_sql", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-site pattern: closed tag registry whose wrong-pick is a security bug, single-boundary wire↔domain brand transform keyed on the cell tag, and mutation helpers that swap (never merge) backend-specific fields while rebranding the body. Adopt the defensive-copy discipline for reactive-store-backed defaults and the documented-honesty of the carry-over NOTE (record the known-bad default instead of hiding it). Adapt the default row limit and the confirmation-less carry-over policy to your product's data. Omit Supabase's specific endpoints/labels. Caveat: the wire/domain transform has no dedicated upstream test — its correctness rests on the consumer tests plus the disjoint-brand compile checks in pass-3's analytics capsule.
