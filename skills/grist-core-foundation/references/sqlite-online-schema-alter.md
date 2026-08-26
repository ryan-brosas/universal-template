<!-- capsule-v2 -->
# Online SQLite schema alter — how do you rename/retype a column without dropping data, when ALTER can't change types or defaults?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How do you apply a column type/default/rename change to a populated SQLite table — choosing the cheap metadata-only path when possible and the safe rebuild path otherwise, while preserving every stored value byte?

## Three-ladder alter: no-op check → explicit-default patch → writable_schema soft edit + opportunistic cell re-encode
**Path/Symbol:** `app/server/lib/DocStorage.ts:_alterColumn` (:1806–1843), `_rebuildTableSql` (:1747–1780), `_alterTableSoft` (:1787–1804), `fixDefault` (:2017–2019). NOTE: despite the name, `_rebuildTableSql` only BUILDS the new CREATE-TABLE text applied via `writable_schema` — no data is ever copied; the tmp-table copy/rebuild ladder lives in `_process_RemoveColumn` (:1289–1316), a different seam.
**Signature:** `private async _alterColumn(tableId: string, colId: string, newColId: string, newColType: string | null = null): Promise<void>`; `_rebuildTableSql(...) => Promise<RebuildResult | null>` (null = nothing changed / column missing).
**Data Shape:** `RebuildResult { sql, oldGristType, newGristType, oldDefault, newDefault, oldSqlType, newSqlType }` — computed from `PRAGMA table_info` rows (`{name, type, dflt_value}`) minus `id`.

### Decisive source
```ts
private async _alterTableSoft(tableId: string, newTableSql: string): Promise<void> {
  // Procedure per https://sqlite.org/lang_altertable.html for changes that do NOT
  // affect on-disk content: rewrite sqlite_master.sql directly.
  const row = await this.get("PRAGMA schema_version");
  const newSchemaVersion = row.schema_version + 1;
  const tmpTableId = DocStorage._makeTmpTableId(tableId);
  await this._getDB().runEach(
    "PRAGMA writable_schema=ON",
    ["UPDATE sqlite_master SET sql=? WHERE type='table' and name=?", [newTableSql, tableId]],
    `PRAGMA schema_version=${newSchemaVersion}`,   // must be bumped by hand
    "PRAGMA writable_schema=OFF",
    // NOT in the official recipe: forces SQLite to notice the edited schema.
    `ALTER TABLE ${tableId} RENAME TO ${tmpTableId}`,
    `ALTER TABLE ${tmpTableId} RENAME TO ${tableId}`,
  );
}
```

**Flow:** `_rebuildTableSql` computes the would-be column spec from PRAGMA; if NOTHING changed → return null (no-op) → else ladder: (1) if the DEFAULT changed, run `UPDATE … SET col=oldDefault WHERE col IS oldDefault` (note `IS` for NULL) so existing "holes" that merely display the default don't silently start storing the NEW one; (2) `_alterTableSoft` edits `sqlite_master.sql` under `writable_schema`, hand-incrementing `schema_version` (valid because Grist doc tables carry no indexes/triggers); (3) opportunistically re-encode: scan cells with `typeof(col)='blob'`, decode with OLD types, re-encode with NEW types, update only results that are no longer BLOBs. (When a column must be REMOVED, `_process_RemoveColumn` uses the classic tmp-table copy ladder instead.)
**Invariant:** The soft alter NEVER touches table data — a type change converts nothing in SQL (the ModifyColumn test asserts ints stay marshalled blobs after Int→Text); conversion happens later through the encode/decode contract, cell-by-cell, only where the result is representable natively ("opportunistic unmarshalling"). Bool→Int sweeps collapse false→0 irreversibly — accepted lossiness, pinned by test. Soft-alter is only valid because Grist tables have no indexes/triggers to invalidate.
**Probe:** `test/server/lib/DocStorage.js` `.ModifyColumn` `"Should modify the column type"` (:557–656) — full matrix incl. opportunistic unmarshal after Text→Int and the documented bool/int collapse.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "_alterColumn _rebuildTableSql _alterTableSoft writable_schema", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder ordering (no-op check → default-hole patch → writable_schema metadata edit → opportunistic cell sweep) for any SQLite-backed dynamic schema; adopt `writable_schema` ONLY with its three non-negotiables: hand-bumped schema_version, the rename-twice cache flush, and no indexes/triggers on the target. Adapt which changes count as "soft" to your engine version (modern SQLite added DROP COLUMN etc.). Omit the bool-collapse tolerance only if your type system has no overlapping scalar representations.
