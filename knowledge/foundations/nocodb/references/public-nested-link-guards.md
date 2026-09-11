<!-- capsule-v2 -->
# Shared nested-link endpoints — what extra guards do the anonymous /mm/ /hm/ picker routes need that authenticated ones don't?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do public relation-listing routes prevent reading links of filtered-out rows, links of hidden columns, or arbitrary related-table fields via ?fields=?

## publicMmList / publicHmList / relDataList guards
**Path/Symbol:** `packages/nocodb/src/services/public-datas.service.ts:publicMmList` (:1009-1122), `publicHmList` (:1124-1236), `relDataList` (:826-1007), shared dataRead (:1238-1290).
**Signature:** `async publicMmList(context, param: { query; sharedViewUuid; password?; columnId; rowId })`.
**Data Shape:** All three resolve view → model → column → related model; mm/hm restrict the response through nocoExecute over a synthetic `{List: 1}` AST with `{nested: {List: param.query}}`.

### Decisive source
```ts
// Verify parent row is visible in the shared view before fetching relations
// — a filtered-out row must not be visible for its relations either.
const parentRow = await baseModel.readByPk(param.rowId, false, {}, { applyViewFilters: true });
if (!parentRow) { NcError.recordNotFound(param.rowId); }

// Block access to relation columns hidden from the shared view so the
// /mm/ endpoint can't be used to read links the view owner stripped.
const isVisible = viewColumns.some((vc) => vc.fk_column_id === column.id && vc.show);
if (!isVisible) { NcError.badRequest('Column not accessible in this shared view'); }
```
```ts
// `extractOnlyPrimaries` below limits the SELECT to pk/pv/display, but the
// predicate is still compiled against the related table's FULL column set —
// a one-bit oracle per non-exposed column, plus `sort` as a reordering
// channel. `/mm/` and `/hm/` already strip; this picker route didn't.
await restrictNestedLinkQueryForColumn(context, column, param.query);
```
and the form-picker fields allowlist (relDataList):
```ts
// A shared form's picker legitimately asks for extra related-table fields ...
// so honour only what the share exposes: pk, pv, the link's custom display
// column, and the far-side targets of lookups/rollups VISIBLE on this form.
const exposedRelatedColumnIds = new Set(model.columns.filter((c) => c.pk || c.pv).map((c) => c.id));
if (colOptions.fk_display_value_column_id) exposedRelatedColumnIds.add(colOptions.fk_display_value_column_id);
for (const id of collectRelatedNeededColumnIds(currentModel.columns.filter((c) => viewColumns.some((vc) => vc.fk_column_id === c.id && vc.show)))) {
  exposedRelatedColumnIds.add(id);
}
```

**Flow:** every route: view type gate (FORM rejected on mm/hm) → password → model null guard ("shared view can outlive its table" — trash soft-deletes ONLY the model row while the share UUID survives) → column belongs-to-model + VIEW-VISIBILITY check (show flag, distinct from authenticated paths' cross-base rule) → **parent-row visibility under applyViewFilters** before any relation fetch → restrictNestedLinkQueryForColumn mutates param.query (data+count read it) → fetch+count → PagedResponse. relDataList adds sanitizePublicQuery + extractOnlyPrimaries:true + the form-picker fields allowlist; dataRead sanitizes and applies view filters as the visibility check for both record reads AND attachment downloads.
**Invariant:** Three independent gates stack: parent-row visibility (row-level), column show-flag (link-level), predicate confinement (related-column level). Skipping ANY one reopens a channel: without applyViewFilters a hidden row's links leak; without show-flag a stripped link leaks; without query restriction a one-bit oracle per non-exposed related column remains in where/sort.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves PublicDatasService.publicMmList/publicHmList; grep confirms two `applyViewFilters: true` readByPk guards (:1068/:1183) and three `restrictNestedLinkQueryForColumn(` calls (:913, :1086, :1201).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "publicMmList applyViewFilters restrictNestedLinkQueryForColumn", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stacked-gates pattern for ANY anonymous endpoint that dereferences relations: visible-parent ⇒ visible-links ⇒ confined-predicate ⇒ allowlisted-fields. Adapt error vocabulary (recordNotFound vs badRequest) to your API conventions. Omit the lookup/rollup far-side allowlist if forms can't embed those.
