<!-- capsule-v2 -->
# Row-color & button-filter AST dependencies — why do hidden columns referenced only by view cosmetics appear in data payloads?

**Source:** NocoDB Sustainable Use License `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory project `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** A column hidden from a view can still drive row coloring or button visibility — how does the AST include exactly those columns without opening the gate to every hidden field?

## Opt-in collectors feeding one dedicated strategy rung
**Path/Symbol:** `packages/nocodb/src/helpers/getAst.ts:getViewRowColorFields` (:370-402) + `getButtonFilterFields` (:409-450); consumed via `includeRowColorColumns`/`includeButtonFilterColumns` params (:127-141) and the `rowColorButtonFieldStrategy` rung (`getAstColumnStrategy.ts:121-127`).
**Signature:** `getViewRowColorFields({ context, view, ncMeta? }): Promise<string[]>`; `getButtonFilterFields({ context, model, view?, ncMeta? }): Promise<string[]>`.
**Data Shape:** Both return deduped column-id arrays (`.filter((value, index, array) => array.indexOf(value) === index)`). Callers must pass the ids into `ColumnAstContext.rowColoringColumnIds` / `buttonFilterFilterColumnIds` Sets; the strategy resolves those columns to `true` regardless of view-hidden status.

### Decisive source
```ts
if (params.view.row_coloring_mode === ROW_COLORING_MODE.SELECT) {
  const viewMeta = parseProp(params.view.meta) as ViewMetaRowColoring;
  return [viewMeta?.rowColoringInfo?.fk_column_id];
} else if (params.view.row_coloring_mode === ROW_COLORING_MODE.FILTER) {
  // … RowColorCondition.getByViewId → metaList2(FILTER_EXP, xcCondition knex
  //   whereIn fk_row_color_condition_id) → filter+dedupe fk_column_id
}
return [] as string[];
```
(:375-401 — SELECT mode reads ONE column id from view.meta; FILTER mode walks row-color conditions to their FILTER_EXP rows; anything else returns empty.)

**Flow:** getAst collects the two id sets BEFORE the per-column loop when flags are set → strategy rung #3 matches any column in either set → resolve returns literal `true`, bypassing the later view-visibility rung by ordering.
**Invariant:** These collectors are the ONLY sanctioned way a view-cosmetic reference widens the payload — the general escape hatch (`allowRequestedHiddenFields`) stays opt-in for authenticated link-pickers and never public.

### Porting traps (each verified against source)
- **Button filters scope to VISIBLE buttons first (:425-432):** with a view present, button columns are filtered to view-visible ones BEFORE their filters are read — hidden-button filters do NOT widen payloads.
- **Both collectors tolerate missing columns:** `.filter((f) => f.fk_column_id)` before mapping; unknown/deleted column ids just drop out.
- **In-file anchors:** `grep -n 'ROW_COLORING_MODE.SELECT' src/helpers/getAst.ts` → :375; `grep -n "whereIn('fk_button_col_id'" src/helpers/getAst.ts` → :442.
- **No direct tests** import these functions (109 spec files grepped; jest bin absent in clone).

**Probe:** Deterministic probe from repo root:
`cd packages/nocodb && grep -c 'fk_row_color_condition_id' src/helpers/getAst.ts` → `1` and `grep -n 'row_coloring_mode' src/helpers/getAst.ts` → `:375` and `:378`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "getButtonFilterFields", limit: 10 });
```
Live-resolved rank-1 line-exact `getButtonFilterFields` :409-450 (total:1).

## Verdict
Adopt the two-mode row-color collector + visible-buttons-first scoping + dedicated strategy rung; adapt ROW_COLORING_MODE enum plumbing to host; omit EE-side lookup widening. Coverage caveat: no direct tests at pin; probes are source-greps.
