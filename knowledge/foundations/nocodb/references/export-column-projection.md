<!-- capsule-v2 -->
# CSV export column projection & BT/FK remap — how does a CSV export decide which columns to emit, and how do belongs-to link columns get rewritten onto their FK child?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** When streaming a table to CSV, how are the emitted columns chosen (server-composed, never client-supplied) and how is a BELONGS_TO link column replaced by its foreign-key child column?

## server-composed field projection + bt→fk substitution
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.streamModelDataAsCsv` (875–1303).
**Signature:** `streamModelDataAsCsv(context, {dataStream, linkStream, baseId, modelId, viewId?, handledMmList?, _fieldIds?, ncSiteUrl?, delimiter?, excludeUsers?, includeCrossBaseColumns?, crossBaseLinkMmModelIds?, filterArrJson?, sortArrJson?, locale?, customConditions?}): Promise<void>`.
**Data Shape:** `_fieldIds?: string[]` is a SERVER-COMPOSED column-id projection (never forwarded from a request payload — it bypasses the ref view's visibility); `fields` = resolved column TITLES; `btMap: Map<fkColId, "base::source::fkModel::linkColId">` rewrites belongs-to cells.

### Decisive source
```ts
// BT / 1:1-with-bt link columns are replaced by their FK child column in the output
if (col.uidt === UITypes.LinkToAnotherRecord &&
    (col.colOptions?.type === RelationTypes.BELONGS_TO ||
     (col.colOptions?.type === RelationTypes.ONE_TO_ONE && col.meta?.bt))) {
  const fkCol = model.columns.find((c) => c.id === col.colOptions?.fk_child_column_id);
  if (fkCol) {
    if (param._fieldIds?.includes(col.id)) {          // swap id in projection
      param._fieldIds.push(fkCol.id);
      param._fieldIds.splice(param._fieldIds.indexOf(col.id), 1);
    }
    btMap.set(fkCol.id, `${col.base_id}::${col.source_id}::${col.fk_model_id}::${col.id}`);
  }
}
// field selection: caller-curated ids OR ref-view visible columns OR all non-link cols
let fields = param._fieldIds
  ? model.columns.filter((c) => param._fieldIds?.includes(c.id)).map((c) => c.title)
  : model.columns.filter((c) => !isLinksOrLTAR(c) && !isVirtualCol(c)).map((c) => c.title);
```

**Flow:** `_fieldIds` (when present) is intersected with `model.columns` so a foreign id resolves to nothing rather than leaking. Without `_fieldIds`, the export honors the reference collaborative view's column visibility/order (`viewCols` sorted by `order`, filtered by `show`, minus hidden system fields) — unless in dataExportMode with caller ids, where the caller's order is kept verbatim. During formatting, each FK cell whose id is in `btMap` is rewritten onto the `base::source::fkModel::linkColId` key (so the importer can reconstruct the link) and the original FK key is deleted.

**Invariant:** the projection is ALWAYS server-derived — a raw client `_fieldIds` must never be trusted because it bypasses view visibility. The BT column never appears in output; only its FK child does, and the mapping is recorded so the link is recoverable. Cross-base link columns are filtered out unless `includeCrossBaseColumns` (or they're in the mm allow-list).

**Probe:** no unit test upstream. Source-grounded probe: `export.service.ts:938-964` (btMap build + `_fieldIds` swap) vs `:966-1016` (field selection branches) and `:1042-1048` (FK→btMap rewrite in `formatData`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "streamModelDataAsCsv btMap _fieldIds fields viewCols", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt server-composed column projection intersected against the model, and BT→FK child substitution with a recoverable mapping; adapt view-visibility resolution and system-field hiding to host. Omit the mm side-stream logic (see import-link-stream capsule). Coverage caveat: no in-repo tests; source-grounded.
