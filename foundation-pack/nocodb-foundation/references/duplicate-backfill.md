<!-- capsule-v2 -->
# External-model backfill — during a table duplicate, how are rows in OTHER tables that link to the copied table patched with the new ids?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the duplicate flow update belongs-to links inside external tables without a full re-copy?

## papaparse step-pause bulkDataUpdate backfill
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/export-import/duplicate.processor.ts:DuplicateProcessor.importModelsData` external-models loop (1090-1257).
**Signature:** `importModelsData(targetContext, sourceContext, {idMap, sourceProject, sourceModels, destProject, destBase, modelFieldIds?, externalModels?, ...})`.
**Data Shape:** `modelFieldIds: Record<modelId, [pkColId, btColId...]>` — per related table: which fields to export (pk + its belongs-to columns pointing at the copied table); CSV placeholder `'__nc_empty_string__'` = empty string.

### Decisive source
```ts
papaparse.parse(dataStream, {
  newline: '\r\n',
  step: async (results, parser) => {
    if (!headers.length) {
      parser.pause();                    // resolve header columns async, then resume
      for (const header of results.data) {
        const id = idMap.get(header);    // source column id → dest column
        ... headers.push(childCol.column_name) or null ...
      }
      parser.resume();
    } else {
      if (results.errors.length === 0) {
        const row = {};
        ... row[headers[i]] = results.data[i] !== '' ? ... : '';
        chunk.push(row);
        if (chunk.length > 1000) {
          parser.pause();
          try {
            // remove empty rows (only pk is present)
            chunk = chunk.filter((r) => Object.keys(r).length > 1);
            if (chunk.length > 0) await this.bulkDataService.bulkDataUpdate(targetContext, {...});
```

**Flow:** for each related model holding belongs-to links at the duplicated table, the source exports ONLY `[pk + those bt columns]` as CSV (`_fieldIds` filter), the stream is reparsed with async header resolution (source col ids → destination column names via idMap), and chunks of 1001+ non-empty rows are bulk-UPDATED into the destination table — rewriting the fk values from old ids to new ids.
**Invariant:** the first data row doubles as the header-resolution trigger and must pause the parser while Column lookups run (async in a sync step callback). Rows containing only the pk (nothing to patch) are filtered before update. This is UPDATE-not-insert: external tables already exist; only their link cells change.
**Probe:** no unit test upstream. Source-grounded probe: `duplicate.processor.ts:1131-1172` — pause/resume around async header mapping; `:1188-1204` — >1000-row flush preceded by the only-pk filter.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "importModelsData externalModels bulkDataUpdate _fieldIds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt field-filtered CSV re-export + bulk-update id remapping for cross-table references; adapt to your id-map transport (in-memory map vs serialized); omit the `__nc_empty_string__` sentinel if your CSV writer distinguishes null/empty natively. Coverage caveat: no in-repo tests; source-grounded.
