<!-- capsule-v2 -->
# ByViewId misnomer — why does "dataReadByViewId" treat its parameter as a MODEL id?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** Which DatasService methods named *ByViewId actually resolve a table, and what breaks if a porter "fixes" the name or the resolution?

## DatasService *ByViewId family
**Path/Symbol:** `packages/nocodb/src/services/datas.service.ts:dataListByViewId` (:624-643), `dataReadByViewId` (:1150-1186), `dataInsertByViewId` (:1188-1212), `dataUpdateByViewId` (:1214-1242), `dataDeleteByViewId` (:1244-1266).
**Signature:** All take `{ viewId: string; ... }` and immediately do `Model.getByIdOrName(context, { id: view?.fk_model_id || param.viewId })` / `Model.getByIdOrName(context, { id: param.viewId })` — the id is resolved as a MODEL id first, view id second.
**Data Shape:** `dataListByViewId` is the only one that loads an actual View (`View.get(context, param.viewId)`) to obtain `fk_model_id`; the read/insert/update/delete quartet pass `param.viewId` STRAIGHT into Model.getByIdOrName.

### Decisive source
```ts
// dataListByViewId :628-635 — real view load, then model via fk_model_id
const view = await View.get(context, param.viewId);
const model = await Model.getByIdOrName(context, {
  id: view?.fk_model_id || param.viewId,
});
if (!model) NcError.get(context).tableNotFound(view?.fk_model_id || param.viewId);
```
```ts
// dataReadByViewId :1155-1158 — no View at all; the "view" id IS the model id
const model = await Model.getByIdOrName(context, { id: param.viewId });
if (!model) NcError.get(context).tableNotFound(param.viewId);
...
} catch (e) {
  if (e instanceof NcError || e instanceof NcBaseError) throw e;
  this.logger.error('Please check server log for more details', e);
  NcError.get(context).internalServerError('Please check server log for more details');
}
```
```ts
// dataInsertByViewId :1197-1201 — the form gate still fires on this path
const view = await View.get(context, param.viewId);
if (view?.type === ViewTypes.FORM) {
  await FormView.validateFormScheduling(context, param.viewId);
}
```

**Flow:** dataListByViewId = genuine view route (view→model→shared engine). The write/read quartet = legacy routes where the path segment historically held a table id; they skip alias resolution entirely, never touch view filters/sorts (no getAst view scoping on read beyond bare model), and funnel through the same baseModel primitives.
**Invariant:** The misnomer is CONTRACT: clients call these with TABLE ids; renaming parameters or "correcting" resolution to View.get would break every existing consumer. Note the asymmetry inside one file — same suffix, two different resolution semantics. Also note the read path's catch rethrows only typed errors (`NcError`, `NcBaseError`) and masks everything else as internalServerError. Insert still honors form scheduling even though this route ignores most view config.
**Probe:** Runner blocked at this pin. Deterministic probe: grep confirms 5 `ByViewId` methods; exactly 2 contain `View.get(` (dataListByViewId :628, dataInsertByViewId :1198); `dataReadByViewId` contains zero view references after model resolution.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "dataReadByViewId getByIdOrName", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt nothing blindly — this capsule exists to prevent an "obvious cleanup" bug. Keep legacy names/resolution verbatim when porting consumers exist; document the misnomer in your leaf's Boundaries. Omit the whole family if you have no legacy API surface to mirror.
