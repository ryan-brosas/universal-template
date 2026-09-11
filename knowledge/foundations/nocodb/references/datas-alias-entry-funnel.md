<!-- capsule-v2 -->
# DatasService alias-entry funnel — why do thin wrappers validate BEFORE delegating to getDataList?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** When porting the v1/v2 `/api/v1/db/data/*` entry service, which checks live in the wrapper and which in the shared engine?

## DatasService entry methods
**Path/Symbol:** `packages/nocodb/src/services/datas.service.ts:dataList` (:28-96), `dataInsert` (:144-176), `dataDelete` (:208-229).
**Signature:** Wrappers resolve `{model, view}` via `getViewAndModelByAliasOrId(context, param)` (helpers/dataHelpers.ts:35-61 — base by titleOrId, model by aliasOrId, view by titleOrId **with** `viewNotFound` error when named-but-missing), then delegate to `this.getDataList(...)` with `throwErrorIfInvalidParams: true`.
**Data Shape:** `param.query.linkColumnId?: string` is the only wrapper-owned read-side option; writes carry `cookie` (typecast flag rides `cookie.query.typecast === 'true'`, :204).

### Decisive source
```ts
// dataList :59-78 — linkColumnId turns a table listing into "rows linked to X"
if (param.query.linkColumnId) {
  const linkColumn = await Column.get<LinkToAnotherRecordColumn>(context, {
    colId: param.query.linkColumnId,
  });
  if (
    !linkColumn ||
    !isLinksOrLTAR(linkColumn) ||
    !linkColumn.colOptions ||
    linkColumn.colOptions.fk_related_model_id !== model.id   // ← must point AT this table
  ) {
    NcError.get(context).fieldNotFound(param.query?.linkColumnId, {
      customMessage: `Link column with id ${...} not found`,
    });
  }
  // The linked rows are rendered through the LINK'S target view, not the caller's
  if (linkColumn.colOptions?.fk_target_view_id) {
    view = await View.get(context, linkColumn.colOptions.fk_target_view_id);
  }
}
```
```ts
// dataInsert :157-159 — form scheduling gates BOTH insert entries
if (view?.type === ViewTypes.FORM) {
  await FormView.validateFormScheduling(context, view.id);
}
// dataDelete :222-228 — external-source delete parity (comment quoted)
// delByPk cleans up link references itself (mm junction rows are deleted,
// hm child FKs are nulled — see shouldCascadeLinkCleanup), the same as for
// meta bases and the v3/data-table delete paths. The old external-only
// hasLTARData guard predated that cascade logic ... Drop it so external
// behaves consistently.
return await baseModel.delByPk(param.rowId, null, param.cookie);
```

**Flow:** resolve alias → (read path) validate linkColumnId belongs to THIS model as LTAR → swap to the link's `fk_target_view_id` when set → delegate to shared engine. Write paths: form-scheduling gate → fresh `baseModel` per call → `nestedInsert`/`updateByPk(typecast)`/`delByPk`.
**Invariant:** Wrapper owns IDENTITY + AUTHORIZATION-adjacent validation (link column must reference this exact model or it is a fieldNotFound, never silently ignored) and VIEW SUBSTITUTION; the engine owns shape/pagination/errors. A porter who moves the `fk_related_model_id !== model.id` check into the engine loses nothing functionally but who omits it lets any colId silently list unlinked rows. Delete relies on `delByPk`'s internal link-cascade (`shouldCascadeLinkCleanup`) — do NOT reintroduce an external-links pre-guard; upstream removed it deliberately for parity.
**Probe:** Runner blocked at this pin — `datas.service.spec.ts` is a 19-line "should be defined" stub. Deterministic probe: grep confirms exactly one `fk_related_model_id !== model.id` comparison and one `fk_target_view_id` view swap inside dataList; spec stub exists but asserts construction only (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "linkColumnId fk_target_view_id", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the funnel split (identity/validation in wrapper, mechanics in engine) and the link-target-view substitution. Adapt error taxonomy to host. Omit the form-scheduling twin if your product has no scheduled forms.
