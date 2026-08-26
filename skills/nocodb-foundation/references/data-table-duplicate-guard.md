<!-- capsule-v2 -->
# Duplicate-row guard — why does a bulk update/delete refuse before touching the DB, and how is a composite pk keyed?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do you reject a bulk payload that names the same row twice BEFORE any DB work, including when the table has a composite primary key?

## DataTableService.checkForDuplicateRow
**Path/Symbol:** `packages/nocodb/src/services/data-table.service.ts:checkForDuplicateRow` (:435-484).
**Signature:** `private async checkForDuplicateRow(context: NcContext, { rows, model }: { rows: any[] | any; model: Model }): Promise<void>`.
**Data Shape:** Input rows as submitted by caller (pk value under title, column_name, OR column id). Composite keys are joined into one string with `___` separators; each component is stringified and `_` escaped to `\\_` first.

### Decisive source
```ts
if (!rows || !Array.isArray(rows) || rows.length === 1) {
  return;
}
await model.getColumns(context);
const keys = new Set();
for (const row of rows) {
  let pk;
  // TODO: refactor to extractPkValues of baseModelSqlV2
  // if only one primary key then extract the value
  if (model.primaryKeys.length === 1)
    pk = row[model.primaryKey.title] ?? row[model.primaryKey.column_name] ?? row[model.primaryKey.id];
  // if composite primary key then join the values with ___
  else
    pk = model.primaryKeys
      .map((pk) => (row[pk.title] ?? row[pk.column_name] ?? row[pk.id])?.toString?.()?.replaceAll('_', '\\_'))
      .join('___');
  if (keys.has(pk)) {
    NcError.get(context).unprocessableEntity('Duplicate record with id ' + pk);
  }
  if (pk === undefined || pk === null) {
    NcError.get(context).unprocessableEntity('Primary key is required');
  }
  keys.add(pk);
}
```

**Flow:** single row or non-array → no-op (the guard is BULK-only) → load columns → per row build the composite key (single-pk shortcut vs `___`-joined components with `_`→`\_` escaping) → duplicate seen ⇒ 422 'Duplicate record with id …' → missing pk ⇒ 422 'Primary key is required' (checked AFTER the dup check, so an all-undefined pair reports the dup first only if both stringify equal) → remember key.
**Invariant:** Runs BEFORE the readonly check / baseModel calls in both dataUpdate and dataDelete (:265, :322) — it is a pre-flight rejection, never a post-hoc cleanup. The `___` join format must match whatever downstream code uses to address composite pks (e.g. extractIdObj consumers), or updates will silently miss. Note the ordering quirk: the undefined/null pk check sits AFTER the duplicate check inside the loop.
**Probe:** No runner at this pin — deterministic probe: search_graph resolves `DataTableService.checkForDuplicateRow` at :435-484; grep confirms exactly two call sites (`dataUpdate` :265, `dataDelete` :322) and none in insert paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "checkForDuplicateRow unprocessableEntity", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pre-flight Set-based duplicate rejection for bulk mutations and the composite-key string encoding with escaping. Adapt the separator literal to your host's pk addressing convention. Omit the single-row early return only if your bulk endpoint never receives length-1 arrays (it does upstream — that IS the contract).
