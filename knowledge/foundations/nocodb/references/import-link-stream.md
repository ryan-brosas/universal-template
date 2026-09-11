<!-- capsule-v2 -->
# Import link stream — how do mm links travel as a separate CSV side-channel during duplicate/import so data rows stay clean?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** Why is there a second `linkStream` next to the data stream, and what does handledLinks dedupe?

## dual-stream export + handledMmList dedup
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/export-import/import.service.ts:ImportService.importDataFromCsvStream/importLinkFromCsvStream`; producers `export.service.ts:streamModelDataAsCsv({dataStream, linkStream, handledMmList})`; consumer loop `duplicate.processor.ts:1040-1079`.
**Signature:** `importLinkFromCsvStream(targetContext, {idMap, linkStream, destProject, destBase, handledLinks}): Promise<handledLinks'>` (returns grown list).
**Data Shape:** linkStream rows = `{mm_table_title, rowId, childId}`-shaped CSV lines; `handledMmList/handledLinks` = array of already-inserted mm model ids.

### Decisive source
```ts
this.exportService.streamModelDataAsCsv(sourceContext, {
  dataStream, linkStream,
  handledMmList: handledLinks,          // skip mm tables already imported
  ...
});
await this.importService.importDataFromCsvStream(targetContext, { idMap, dataStream, ... });
handledLinks = await this.importService.importLinkFromCsvStream(targetContext, {
  idMap, linkStream, ..., handledLinks,
});                                     // returns EXTENDED list for the next model
```

**Flow:** when exporting a table whose rows contain many-to-many columns, the mm association rows would be duplicated per table pair; instead the exporter emits association tuples onto a dedicated side stream and skips any mm table already present in handledMmList. The importer drains that stream AFTER the table's data rows exist (links need both pks), translating both endpoints through idMap, then reports back the grown list.
**Invariant:** order matters — data first, then links; a link row referencing an uninserted parent fails or orphans. handledLinks must persist ACROSS models within one duplication run (it's passed by value out of each call), otherwise shared mm tables insert twice. Both streams push(null) on producer error so consumers finish and the error surfaces post-join.
**Probe:** no unit test upstream. Source-grounded probe: `duplicate.processor.ts:1025` (`let handledLinks = []` outside the model loop) vs `:1070-1079` reassignment from importLinkFromCsvStream return.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "importLinkFromCsvStream linkStream handledMmList", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt side-channel streams for relation tuples with cross-model dedup lists; adapt wire format to your transport; omit CSV specifics if you pass structured batches. Coverage caveat: no in-repo tests; source-grounded.
