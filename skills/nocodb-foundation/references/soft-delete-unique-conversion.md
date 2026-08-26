<!-- capsule-v2 -->
# Soft-delete unique conversion — how do you keep UNIQUE guarantees alive when rows are soft-deleted instead of removed?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does adding a soft-delete flag force every plain UNIQUE constraint to become a partial unique index, and which columns are exempt?

## Four-flag decision + column-order SQL emission
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_010_soft_delete_column.ts` — v1 FK detection (:314-339), needs* flags (:341-364), `needsUniqueRecreate` (:372-377), originalColumns/existingColumns shaping (:379-396), NEW-before-UPDATE ordering comment + `columns = [...newColumns, ...existingColumns]` (:398-442), index creation (:451-462).
**Signature:** `needsUniqueRecreate(c) = (needsDeletedCol || needsUniqueConversion) && c.unique && !v1OoFkColIds.has(c.id) && !c.pk && !c.ai`.
**Data Shape:** `v1OoFkColIds: Set<string>` of v1 one-to-one FK ids found by joining COL_RELATIONS on `fk_child_column_id` with `type='oo'`, `version IS DISTINCT FROM 2`, child column `unique=true`.

### Decisive source
```ts
// PgClient.tableUpdate emits SQL in column order, and partial unique
// indexes on existing columns reference __nc_deleted in their WHERE
// predicate — so NEW_COLUMN additions must come before UPDATE_COLUMN edits.
const newColumns: any[] = [];
if (needsDeletedCol) {
  newDeletedColumn = {
    ...(await memoizedGetColumnPropsFromUIDT(source, UITypes.Deleted, '__nc_deleted')),
    column_name: getUniqueColumnName(model.columns, '__nc_deleted'),
    title: getUniqueColumnAliasName(model.columns, '__nc_deleted'),
    // SQLite/MySQL store booleans as integers:
    cdf: ['mysql2','mysql','sqlite3'].includes(source.type) ? '0' : 'false',
    system: true,
    altered: Altered.NEW_COLUMN,
  };
  newColumns.push({ ...newDeletedColumn, cn: newDeletedColumn.column_name });
}
const existingColumns = model.columns.map((c) => ({
  ...c, cn: c.column_name, cno: c.column_name,
  ...(v1OoFkColIds.has(c.id) ? { altered: Altered.UPDATE_COLUMN, unique: false }
   : needsUniqueRecreate(c) ? { altered: Altered.UPDATE_COLUMN } : {}),
}));
await sqlMgr.sqlOpPlus(source, 'tableUpdate', { ...model, tn, originalColumns, columns: [...newColumns, ...existingColumns] });
```

**Flow:** detect v1 one-to-one FK columns (they need their unconditional unique DROPPED because the v1→v2 link upgrade re-creates them differently) → compute the four needs flags; skip the model entirely if none → mark user-set unique columns (`!pk && !ai`) for UPDATE_COLUMN so the SQL client recreates them as PARTIAL unique indexes excluding `__nc_deleted`-true rows → emit new columns BEFORE edited columns because the partial index WHERE references the not-yet-added flag column → after the table rewrite, create the plain `nc_deleted_idx_<model.id>` index and flush.
**Invariant:** PK and auto-increment uniques must stay UNCONDITIONAL (excluded from conversion both in the flag check and in `hasUniqueColumns`); the false→true `unique` transition on originalColumns is what tells PgClient to rebuild as partial — setting it only on `columns` is not enough. The `cdf` dialect split is the exact bug `_011` exists to repair ('false' string on SQLite compares never-equal to integer 0). Column order inside the tableUpdate body is load-bearing, not cosmetic.
**Probe:** no unit test upstream. Source-grounded probe: exclusion appears twice consistently (:351-353 hasUniqueColumns, :372-377 needsUniqueRecreate); ordering comment at :398-400 precedes the splice at :442; index name `nc_deleted_idx_${model.id}` matches the name `_011` drops/recreates.
**Coverage caveat:** no in-repo tests; pinned from whole-file read.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "needsUniqueRecreate __nc_deleted Altered.UPDATE_COLUMN tableUpdate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exempt-column rule (pk/ai stay unconditional) and new-before-edited emission order whenever soft delete meets unique constraints; adapt the flag names to your schema; omit the v1-FK special case if you have no legacy link format.
