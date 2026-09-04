<!-- capsule-v2 -->
# SQLite boolean default repair — why must value normalization come AFTER the DDL change-column dance, and why drop the index first?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** When a shipped migration wrote a string-typed boolean default on SQLite, what is the safe order of DDL rewrite, data fix, and index surgery?

## DDL-then-data ladder over one column
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_011_normalize_soft_delete_sqlite.ts` — bug explanation header (:19-43), idempotence guards (:252-254), index drop-before-alter (:281-292), sqlMgr tableUpdate (:294-299), flush + recreate index + value normalization (:301-314), meta cdf sync (:316-324).
**Signature:** guards: `if (!deletedCol) return; if (deletedCol.cdf === '0') return;` then per model: `DROP INDEX IF EXISTS` → `sqlOpPlus('tableUpdate', … Altered.UPDATE_COLUMN cdf:'0')` → `flushSourceQueries` → `CREATE INDEX IF NOT EXISTS` → two targeted UPDATEs → `metaUpdate({cdf:'0'})`.
**Data Shape:** `__nc_deleted` rows hold the strings `'false'`/`'true'` (stored verbatim — SQLite has no native boolean); the soft-delete filter compares against INTEGER 0, so every legacy row reads as deleted.

### Decisive source
```ts
// Job 010 is now fixed to use `'0'` as the default for SQLite… Existing
// affected installs need this one-time pass to:
//   - rewrite the physical column's DDL default from 'false' to '0'
//   - normalize surviving row values ('false' → 0, 'true' → 1) AFTER the
//     DDL rewrite: SqliteClient's change-column dance copies the old column
//     into the new one (`UPDATE new = old`), so any normalization done
//     beforehand would be overwritten by the copy.
await realDbDriver.raw('DROP INDEX IF EXISTS ??', [indexName]);       // nc_deleted_idx_<modelId>
await sqlMgr.sqlOpPlus(source, 'tableUpdate', { ...model, tn, originalColumns,
  columns: model.columns.map((c) => c.id === deletedCol.id
    ? { ...c, cdf: '0', altered: Altered.UPDATE_COLUMN } : c) });
await Upgrader.flushSourceQueries(source, realDbDriver);
await realDbDriver.raw('CREATE INDEX IF NOT EXISTS ?? ON ?? (??)', [indexName, tn, deletedCol.column_name]);
await realDbDriver(tnPath).update({ [deletedCol.column_name]: 0 }).where(deletedCol.column_name, 'false');
await realDbDriver(tnPath).update({ [deletedCol.column_name]: 1 }).where(deletedCol.column_name, 'true');
await ncMeta.metaUpdate(ctx.workspace_id, ctx.base_id, MetaTable.COLUMNS, { cdf: '0' }, deletedCol.id);
```

**Flow:** select only sqlite3 meta/local sources → per model find the deleted col and skip if already numeric-defaulted → drop the flag index BEFORE the alter because SqliteClient's rename/add/copy/drop dance renames the original column (the index follows the rename) and SQLite refuses DROP COLUMN on an indexed column → run the change-column DDL through upgrader mode → recreate the index → only now flip stored `'false'/'true'` strings to integers → record the numeric default in `nc_columns_v2.cdf`.
**Invariant:** ORDER IS THE CONTRACT: normalizing values before the DDL is silently undone by the copy step (`UPDATE new = old`), and dropping the index after the alter fails outright. A porter who "simplifies" by doing data-first reimports the empty-table bug this job fixes. The whole job is scoped by construction: non-sqlite sources and `cdf === '0'` models exit early, making reruns free.
**Probe:** no unit test upstream. Source-grounded probe: the header comment :19-43 states the failure mode ("every row is treated as deleted and the UI renders empty tables") and both ordering rationales verbatim; guard pair at :252-254.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "NormalizeSoftDeleteSqliteMigration deletedCol cdf DROP INDEX CREATE INDEX", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the DDL→data→meta-sync ordering plus drop-index-first rule for any SQLite column-type migration; adapt the specific values; omit the meta-cdf sync if your schema has no mirrored column-definition table.
