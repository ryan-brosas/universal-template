<!-- capsule-v2 -->
# LTAR update is a placeholder — why does the model's update() silently do nothing, and where must callers write instead?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** If you port the link-column model, which mutable fields exist, and what happens if a porter assumes `update()` persists them?

## LinkToAnotherRecordColumn.update (placeholder) vs the real writers
**Path/Symbol:** `packages/nocodb/src/models/LinkToAnotherRecordColumn.ts:update` (:303-312) — placeholder; real writers: `insert` (:222-258), and raw metaUpdate call sites e.g. `packages/nocodb/src/services/meta-diffs.service.ts:TABLE_RELATION_CHANGED` (:1084-1105).
**Signature:** `static async update(_context: NcContext, _fk_column_id: string, _param: { fk_target_view_id?: string | null; fk_display_value_column_id?: string | null })` — parameters are deliberately underscore-prefixed and unused.
**Data Shape:** The two fields this API surface owns are `fk_target_view_id` (which view of the related table to project) and `fk_display_value_column_id` (custom display column for the link). Storage row = MetaTable.COL_RELATIONS keyed by fk_column_id.

### Decisive source
```ts
static async update(
  _context: NcContext,
  _fk_column_id: string,
  _param: {
    fk_target_view_id?: string | null;
    fk_display_value_column_id?: string | null;
  },
) {
  // placeholder method
}
```
and the pattern that actually mutates COL_RELATIONS (from meta-diffs.service.ts):
```ts
await Noco.ncMeta.metaUpdate(
  context.workspace_id,
  context.base_id,
  MetaTable.COL_RELATIONS,
  { dr: change.dr },
  { fk_column_id: change.colId },
);
await NocoCache.del(context, `${CacheScope.COL_RELATION}:${change.colId}`);
await NocoCache.del(context, `${CacheScope.COLUMN}:${change.colId}`);
```

**Flow:** insert() writes via extractProps over an explicit allowlist (includes the cross-base ids, order-column ids, version, dr/ur/fk_index_name) then re-reads through cache; reads go through `COL_RELATION:<colId>` cache scope; updates bypass the model class entirely — services call ncMeta.metaUpdate directly AND hand-evict BOTH the COL_RELATION and COLUMN cache entries.
**Invariant:** Never "fix" the placeholder into a working generic update without auditing callers: upstream code that needs mutation goes straight to metaUpdate + manual dual-cache eviction. A porter who calls `update()` expecting persistence gets silent success with NO write — the underscore params mark intent exactly like the csv-detector stub contract mined in pass 7.
**Probe:** No runner at this pin — deterministic probes: search_graph resolves `LinkToAnotherRecordColumn.update` :303-312; grep confirms the body is only a comment; grep for `COL_RELATION:` in meta-diffs.service.ts shows the paired del of both scopes (:1096-1103).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "COL_RELATIONS metaUpdate LinkToAnotherRecordColumn", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the explicit-allowlist extractProps insert and the dual-scope (relation+column) cache eviction on any direct meta write. Adapt field names to your schema. Omit nothing silently: if you implement update() for real, mirror the metaUpdate+evict pair shown above or you fork the caching discipline.
