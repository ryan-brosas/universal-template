<!-- capsule-v2 -->
# Table-editor sensitive-column masking plane — how do you mask sensitive columns by default while letting users persistently override, without losing toggles across table updates?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** A grid shows catalog tables whose column COMMENTS may mark data sensitive; the default is masked, the user can reveal per column, and that choice must survive table re-fetches and reloads — how is the masked set computed and persisted without drift?

## Comment-marker defaults minus persisted user toggles (`state/table-editor-table.tsx`)
**Path/Symbol:** `apps/studio/state/table-editor-table.tsx` : `SENSITIVE_DATA_MARKER` (:21), `isSensitiveDataColumn` (:22-24), `userToggledColumns` init (:59), `userToggledSensitiveColumns`/`temporarilyRevealedColumns` (:116-117), `toggleSensitiveDataColumn` (:118-125), `sensitiveDataColumns` getter (:126-138).
**Signature:** `get sensitiveDataColumns(): Set<string>` (computed live on the valtio proxy).
**Data Shape:** a column is sensitive-by-default iff its COMMENT contains the substring `[SENSITIVE]`. The masked set is a GETTER, not stored state: `defaults − userToggledSensitiveColumns`, where the toggle set holds columns the user explicitly revealed ("Track which columns user has toggled OFF from their default masked state"). Two separate sets: `userToggledSensitiveColumns` (persistent) vs `temporarilyRevealedColumns` (session-only, non-persisted) — a two-tier reveal.

### Decisive source
```ts
const SENSITIVE_DATA_MARKER = '[SENSITIVE]'
const isSensitiveDataColumn = (comment: string | null | undefined): boolean => {
  return comment ? comment.includes(SENSITIVE_DATA_MARKER) : false
}
```
```ts
get sensitiveDataColumns() {
  // Single source of truth: columns marked sensitive = defaults minus user toggles (persistent only)
  const defaultSensitiveColumns = new Set(
    state.table.columns
      .filter((col) => isSensitiveDataColumn(col.comment))
      .map((col) => col.name)
  )
  return new Set(
    Array.from(defaultSensitiveColumns).filter(
      (col) => !state.userToggledSensitiveColumns.has(col)
    )
  )
}
```

**Flow:** comment metadata arrives with the entity → getter recomputes on every read → grid masks accordingly; user toggle mutates only the persistent set; a NEW sensitive column appears masked automatically (it's in defaults, not in toggles), a REMOVED one disappears from both.
**Invariant:** derive the effective policy set (defaults − overrides) instead of storing it — the marker lives in server-side metadata that changes out from under the client, so any stored copy of "which columns are masked" drifts; store only the USER'S decisions, which are stable across refetches.
**Probe:** direct read at the pin; no dedicated test for the masking state — recorded absence. Vitest unexecutable in-lane — never claimed passing.

## Toggle preservation across table updates + the valtio ref() corruption guard (`state/table-editor-table.tsx`)
**Path/Symbol:** same file : `updateTable` (:72-100), toggle preservation (:86-92), ref guard (:96-99), identity-based update detection (:302-308).
**Signature:** `updateTable(table: Entity): void` on the state proxy.
**Data Shape:** on every entity update, saved toggles are filtered to columns that STILL EXIST (`currentColumnNames` membership) before being written back — stale toggles for dropped columns are cleared, surviving ones preserved. Then the new table is assigned — but ONLY after `ref()` captures it raw.

### Decisive source
```ts
// Preserve user's toggle choices across table updates
// Only clear toggles for columns that no longer exist
const currentColumnNames = new Set(table.columns.map((col) => col.name))
const preservedToggles = new Set(
  Array.from(state.userToggledSensitiveColumns).filter((col) => currentColumnNames.has(col))
)
state.userToggledSensitiveColumns = proxySet(preservedToggles)

state.table = supaTable
state.gridColumns = gridColumns
// ref() must run before the assignment below — otherwise valtio's proxy() would wrap
// and mutate `table`'s nested properties in place, corrupting the shared react-query cache object
state._originalTableRef = ref(table)
state.originalTable = table
```

**Flow:** react-query delivers a new entity → effect compares `state._originalTableRef !== table` (identity check is safe because "react-query is good about returning objects with the same ref / different ref") → updateTable re-projects grid columns, prunes dead toggles, stores the raw ref, then assigns.
**Invariant:** (a) when merging user preferences into refreshed server state, prune by CURRENT membership, not by diffing old-vs-new — a column renamed away must not keep a ghost toggle; (b) when a reactive-state library wraps assigned values in proxies, capture the RAW reference BEFORE assignment if you need to compare or hand the object elsewhere — assigning first lets the wrapper mutate the shared upstream (here the react-query cache) in place.
**Probe:** direct read at the pin; no dedicated test — recorded absence.

## Persistence wiring: subscription-triggered debounced save + sensitive-copy warning (`state/table-editor-table.tsx`, `components/grid/SupabaseGrid.utils.ts`)
**Path/Symbol:** `apps/studio/state/table-editor-table.tsx` : subscribe→save effect (:288-300); `components/grid/SupabaseGrid.utils.ts` : `handleCellKeyDown` sensitive-copy toast (:309).
**Signature:** `subscribe(state, () => saveTableEditorStateToLocalStorageDebounced({ gridColumns, projectRef, tableId, sensitiveDataColumns: Array.from(state.userToggledSensitiveColumns) }))`.
**Data Shape:** the valtio subscription is the save trigger — any state change (column moves, sizes, toggles) schedules a 500ms-debounced partial save (pass-6 table-editor-prefetch-parse-plane covers the merge semantics); the toggle set is serialized as a plain array under the `sensitiveDataColumns` key and re-hydrated at state creation (`(savedState as any)?.sensitiveDataColumns ?? []`). Copying a cell from a currently-masked column fires a WARNING toast 'Copied sensitive data to clipboard' (vs success for normal cells) — the mask is a display control, not a clipboard block.

### Decisive source
```ts
useEffect(() => {
  if (typeof window !== 'undefined') {
    return subscribe(state, () => {
      saveTableEditorStateToLocalStorageDebounced({
        gridColumns: state.gridColumns,
        projectRef,
        tableId: state.table.id,
        sensitiveDataColumns: Array.from(state.userToggledSensitiveColumns),
      } as any)
    })
  }
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [])
```

**Flow:** toggle → proxy mutation → subscription fires → debounced partial save to both storage tiers → next session/state-creation re-hydrates the set → getter recomputes masked columns.
**Invariant:** persist user overrides via the state library's own change subscription (one trigger point, debounced) rather than per-action save calls — and treat display masking as UX, not security: warn loudly on copy of masked data instead of silently blocking it.
**Probe:** direct read at the pin; no dedicated test — recorded absence.

## Get live surrounding code
**Retrieve:** Codebase Memory MCP was NOT connected in this session; per AGENTS.md fallback this seam was confirmed by direct source reads at the pin. Revalidate with:
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "SENSITIVE_DATA_MARKER sensitiveDataColumns userToggledSensitiveColumns temporarilyRevealedColumns ref() must run before", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: marker-in-metadata defaults with the effective set DERIVED (defaults − persisted user overrides) rather than stored; two-tier reveal (persistent toggle vs temporary session set); membership-pruned preference merge on every refresh; raw-reference capture before reactive-proxy assignment to protect shared upstream caches; identity-based update detection over a stable-ref data layer; subscription-triggered debounced partial persistence; and warn-don't-block clipboard semantics for masked data. Adapt the marker string, storage keys, and the state library to your stack. Omit Supabase-product specifics: the exact toast wording, valtio wiring, and platform grid components. Direct-test caveat: no dedicated tests exist for this plane (recorded absence); vitest unexecutable in-lane — never claimed passing.
