<!-- capsule-v2 -->
# Soft-delete meta fast path — how does a migration insert system columns + view-column rows without paying per-row service reads?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How do you bulk-insert a new column's meta row and its per-view rows when the normal service methods cost 3-4 reads per call?

## Allowlisted direct inserts + one multi-row INSERT per table
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_010_soft_delete_column.ts` — VIEW_TYPE_TO_COLUMN_TABLE map (:33-42), NC_COLUMNS_V2_FIELDS allowlist (:510-544), `queueSystemColumn` (:546-620), LIST-level fk_level_id wiring (:488-498, :605-608), grid width default (:602-604).
**Signature:** `metaInsert2(workspace_id, base_id, MetaTable.COLUMNS, columnInsertObj) → row.id`; then per view `ncMeta.genNanoid(table)` ids grouped into `knex(table).insert(rows).toQuery()` pushed via `ncMeta.pushUpgraderQuery(sql)`.
**Data Shape:** view-column row = `{id, fk_workspace_id, base_id, fk_view_id, fk_column_id, source_id: view.source_id, show: false, order, created_at, updated_at, width? (grid), fk_level_id? (list)}`.

### Decisive source
```ts
// Allowlist of real nc_columns_v2 columns (mirrors Column.insert's
// extractProps). newCol carries migration-internal fields like `altered`
// that must NOT be forwarded to the SQL INSERT.
const NC_COLUMNS_V2_FIELDS = ['id','fk_model_id','column_name','title','uidt',
  'dt','np','ns','clen','cop','pk','rqd','un','ct','ai','unique','cdf','cc',
  'csn','dtx','dtxp','dtxs','au','pv','order','base_id','source_id','system',
  'meta','internal_meta','virtual','description','readonly'] as const;

const queuedWrites: Promise<any>[] = [];
const queueSystemColumn = (newCol: any, order: number) => {
  const columnInsertObj = { fk_model_id: model.id, source_id, system: true, order };
  for (const k of NC_COLUMNS_V2_FIELDS) {
    if (['fk_model_id','source_id','system','order','meta'].includes(k)) continue;
    if (newCol[k] !== undefined) columnInsertObj[k] = newCol[k];
  }
  queuedWrites.push(
    ncMeta.metaInsert2(ctx.workspace_id, ctx.base_id, MetaTable.COLUMNS, columnInsertObj)
      .then(async (row) => {
        const insertedColId = row.id;              // genNanoid inside metaInsert2
        const byTable = new Map<MetaTable, any[]>();
        for (const view of views) {                 // views pre-fetched ONCE above
          const table = VIEW_TYPE_TO_COLUMN_TABLE[view.type];
          if (!table) continue;
          byTable.get_or_init(table).push({ id: await ncMeta.genNanoid(table),
            fk_view_id: view.id, fk_column_id: insertedColId,
            show: false, order, ... });
        }
        for (const [table, rows] of byTable)
          ncMeta.pushUpgraderQuery(ncMeta.knexConnection(table).insert(rows).toQuery());
      }));
};
```

**Flow:** pre-fetch all views + LIST-view levels once (shared across both possible new columns) → for each new system column build an allowlist-filtered insert object (migration-only fields like `altered`, plus computed defaults for fk_model/source/system/order/meta, never forwarded raw) → chain off the returned column id to fan out one view-column row per view → group rows BY TARGET TABLE and emit one multi-row INSERT per table through the upgrader query queue → run everything in the single flush from soft-delete-upgrader-mode.
**Invariant:** bypassing `{Grid,Form,…}ViewColumn.insert` is safe ONLY because these are `system: true` columns hidden in UI regardless — ordering/visibility/width are semantically irrelevant, so sane constants replace 3-4 live reads per call. Forgetting the allowlist forwards `altered`/`cn` into SQL and breaks the insert; per-row metaInsert2 for view columns would re-introduce the N+1 this exists to kill. LIST views need `fk_level_id` or their rows orphan.
**Probe:** no unit test upstream. Source-grounded probe: allowlist comment (:507-509); grid-width + level branches (:602-608); grouping loop :613-617 emits exactly one pushUpgraderQuery per distinct view-column table.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "queueSystemColumn metaInsert2 VIEW_TYPE_TO_COLUMN_TABLE pushUpgraderQuery", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the allowlisted-direct-insert pattern for any hot migration writing system columns; adapt the field list to your meta schema; omit the LIST/grid special cases if you lack those view types.
