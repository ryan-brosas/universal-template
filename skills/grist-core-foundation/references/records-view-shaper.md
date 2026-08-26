<!-- capsule-v2 -->
# Records-view shaper — how do you turn column-oriented storage into the record JSON clients expect, with hidden-field and exception policy in one place?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Where do id/manualSort/gristHelper filtering, error-cell surfacing, and attachment-metadata cleaning live so every list endpoint stays consistent?

## asRecords transposes TableColValues→[{id,fields}] once; typed cellFormat keeps exceptions inline instead of diverting them to an errors map
**Path/Symbol:** `app/server/lib/DocApi.ts:asRecords` (:229–263), `readTable` (:196–218), `cleanAttachmentRecord` (:340–344); consumers: GET `/records` (:281–289), POST `/records/list` (:292–300), attachments listing (:347–354).
**Signature:** `asRecords(columnData: TableColValues, opts?: {optTableId?; includeHidden?; includeId?; cellFormat?}): TableRecordValue[]`; `readTable(req, activeDoc, tableId, filters, params & {immediate?})`.
**Data Shape:** input is column-oriented `{colId: values[]}` + `id[]`; output row-oriented `{id, fields}`. Hidden set = `manualSort` + any `gristHelper_*` column. Exceptions are raised-formula sentinels `[marker, message]` detected via `isRaisedException`.

### Decisive source
```ts
const fieldNames = Object.keys(columnData).filter((k) => {
    if (!opts?.includeId && k === "id") { return false; }
    if (!opts?.includeHidden && (k === "manualSort" || k.startsWith("gristHelper_"))) { return false; }
    return true;
});
const keepExceptions = (opts?.cellFormat === "typed");
return columnData.id.map((id, index) => {
    const result: TableRecordValue = { id, fields: {} };
    for (const key of fieldNames) {
      let value = columnData[key][index];
      if (!keepExceptions && isRaisedException(value)) {
        _.set(result, ["errors", key], (value as string[])[1]);   // divert to per-row error map
        value = null;
      }
      result.fields[key] = value;
    }
    return result;
});
```
**Flow:** `readTable` validates filter shape (non-array filter value → 400), fetches via sandbox (`fetchQuery` unless `immediate=true`, which skips waiting for doc initialization), pulls table columns for non-meta tables (metaTables skip column inference for sort), then applies sort/limit parameters. `asRecords` then transposes with the three policies above. Attachment listing reuses it against `_grist_Attachments` and additionally projects fields down to `{fileName, fileSize, timeUploaded ISO}`.
**Invariant:** hidden-column filtering and error diversion happen at THIS single choke point — endpoints that bypass asRecords leak manualSort/gristHelper columns or raw exception arrays. `cellFormat=typed` is opt-in per request; default behavior silently nulls failed cells and moves messages to `errors[key]`. The id column is excluded from fields by default because it's already the record key.
**Probe:** `test/server/lib/docapi/DocApiRecords.ts` (list/CRUD suites) and DocApiQueryParameters.ts (sort/limit/filter matrix); coverage caveat: gristHelper filtering edge cases pinned by source reading.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "asRecords readTable applyQueryParameters cleanAttachmentRecord isRaisedException", limit: 8,
  fields: ["signature", "name", "file"] });
```
**Verdict:** Adopt one transpose-and-policy function per API family instead of per-endpoint ad-hoc shaping. Adapt the hidden-prefix convention to yours. Omit typed-exception passthrough if your engine can't raise per-cell.
