<!-- capsule-v2 -->
# Shared view-meta trashed-table guard — why must a soft-deleted model be caught on BOTH cache paths?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** A shared view's UUID outlives its table — where exactly does the public schema endpoint turn that into a clean 4xx instead of a 500?

## PublicMetasService.viewMetaGet
**Path/Symbol:** `packages/nocodb/src/services/public-metas.service.ts:viewMetaGet` (:39-224); guard at :69-80; rangeColumns at :93-156.
**Signature:** `viewMetaGet(context, { sharedViewUuid, password })` → password verified via `View.verifyPassword(view, param.password)` BEFORE any base/model work.
**Data Shape:** Returns the full view meta (filters, sorts, columns, relatedMetas, users) as a shallow copy with `password: undefined`.

### Decisive source
```ts
// :60-67 — lock forced open + eager loads before the guard
view.lock_type = ViewLockType.Collaborative;
await view.getFilters(context);
await view.getSorts(context);
await view.getViewWithInfo(context);
await view.getColumns(context);
await view.getModelWithInfo(context);

// :69-80 — THE GUARD (comment quoted verbatim):
// A shared view can outlive its table: trashing a table soft-deletes only
// the model row (Model.softDelete), leaving the view + its share UUID intact.
// View.getByUUID still resolves, but the model is gone. The shared frontend
// calls viewMetaGet first to load the schema, so guard here to return a clean
// 4xx instead of a 500 on page load, before the data endpoints are reached.
//
// Two cases to cover: Model.getWithInfo returns null on a cache-miss (DB query
// filters soft-deleted rows) → view.model is unset; on a cache-hit it returns
// the cached row without re-checking the flag → view.model.deleted is true.
if (!view.model || view.model.deleted) {
  NcError.get(context).tableNotFound(view.fk_model_id);
}
```
```ts
// :93-96 — why range columns bypass the visibility filter:
// Required for Calendar / Timeline views — the date columns that drive
// the bar / event positions are usually hidden in the field menu, so the
// visibility filter below would drop them from view.model.columns and
// leave the shared frontend with no range columns to render.
const rangeColumns = [];
if (view.type === ViewTypes.CALENDAR) { ... fk_from_column_id / fk_to_column_id ... }
else if (view.type === ViewTypes.TIMELINE) { ... both from and to ... }
```

**Flow:** getByUUID → verifyPassword → base-type check → force `lock_type = Collaborative` (shared viewers can never hit a locked-view error) → eager-load filters/sorts/view-with-info/columns/model-with-info → **dual-case deleted-model guard** → model columns load → source stamping (`view.client`, `view.source{id,type,is_meta,is_local}`) → column visibility filter (show OR required-new OR pk OR group-by OR bt-child-of-shown-link OR lookup/rollup-over-this-column, PLUS rangeColumns exemption checked FIRST) → relatedMetas extraction+projection → optional users block (User/created-by columns ⇒ base user list with emails blanked) → prototype-preserving strip copy.
**Invariant:** The two guard cases exist because the model cache and the DB disagree about soft-deleted rows: miss ⇒ null, hit ⇒ stale object with `.deleted`. Guarding only one case ships either a 500 (null deref downstream) or a leaked "deleted" schema. Range-column exemption must precede the generic visibility filter or Calendar/Timeline shares render positionless. `lock_type` overwrite is deliberate: share links bypass view locking entirely.
**Probe:** Runner blocked at this pin — `public-metas.service.spec.ts` is a construction-only stub. Deterministic probe: grep confirms exactly one `!view.model || view.model.deleted` conjunction in src; exactly one `rangeColumns.includes(` occurrence preceding the `!column` bail (:121-125).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "viewMetaGet getByUUID verifyPassword", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-case soft-delete guard pattern for ANY resource whose share token outlives its owner. Adapt error taxonomy. Omit the range-column exemption if you have no calendar/timeline shares.
