<!-- capsule-v2 -->
# Link-stream import — how do mm junction rows from the side CSV stream get grouped per junction table and bulk-inserted with lazy column resolution?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does `importLinkFromCsvStream` turn the `{column, child, parent}` link rows into per-junction-table bulk inserts, resolving the mm column lazily on first sight?

## lazy mm-column resolution + per-junction chunk buckets
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/export-import/import.service.ts:ImportService.importLinkFromCsvStream` (2565–2718).
**Signature:** `importLinkFromCsvStream(context, {idMap, linkStream, destProject, destBase, handledLinks}): Promise<string[]>` (returns the grown handledLinks list).
**Data Shape:** link rows = `{column, child, parent}` (mm column id, child pk, parent pk); `lChunks: Record<fk_mm_model_id, {parent, child}[]>` buckets rows per junction table; `mmColumns: Record<columnId, Column>` + `mmParentChild: Record<mmModelId, {parent, child}>` caches.

### Decisive source
```ts
papaparse.parse(linkStream, {
  newline: '\r\n',
  step: async (results, parser) => {
    if (!headersFound) { /* find child/parent/column indices from header row */ headersFound = true; }
    else if (results.errors.length === 0) {
      const child = results.data[childIndex], parent = results.data[parentIndex], columnId = results.data[columnIndex];
      if (child && parent && columnId) {
        if (mmColumns[columnId]) {                       // known mm column -> push to its bucket
          const mmModelId = mmColumns[columnId].colOptions.fk_mm_model_id;
          const mm = mmParentChild[mmModelId];
          lChunks[mmModelId].push({ [mm.parent]: parent, [mm.child]: child });
        } else {                                         // first sight -> resolve + flush prior buckets
          parser.pause();
          try { await insertChunks(); } catch (e) { parser.abort(); reject(e); return; }
          const col = await Column.get(context, { source_id: destBase.id, colId: findWithIdentifier(idMap, columnId) });
          if (col) {
            const colOptions = await col.getColOptions(context);
            const vChildCol = await colOptions.getMMChildColumn(context);
            const vParentCol = await colOptions.getMMParentColumn(context);
            mmParentChild[col.colOptions.fk_mm_model_id] = { parent: vParentCol.column_name, child: vChildCol.column_name };
            mmColumns[columnId] = col;
            handledLinks.push(col.colOptions.fk_mm_model_id);
            lChunks[col.colOptions.fk_mm_model_id] = [];
            lChunks[col.colOptions.fk_mm_model_id].push({ /* this row */ });
          }
          parser.resume();
        }
      }
    }
  },
  complete: async () => { await insertChunks(); resolve(handledLinks); },
});
```

**Flow:** the header row fixes the `child`/`parent`/`column` column indices. Data rows are bucketed by junction-table id (`lChunks`). The FIRST time an mm column id is seen, the parser pauses, all previously accumulated buckets are flushed, and the mm column is resolved through `findWithIdentifier(idMap, columnId)` → its mm model's parent/child column names are cached, the bucket is created, and the id is pushed onto `handledLinks`. Subsequent rows for that column just push into the cached bucket. On `complete`, remaining buckets flush and the grown `handledLinks` is returned.

**Invariant:** junction rows must be inserted AFTER their parent/child data rows exist (both pks must be present), and `handledLinks` must persist ACROSS models within one duplication run — it's passed in and returned out so a shared mm table is not inserted twice (the exporter skips mm tables already in the list). Flushing happens only on first-sight of a new mm column (to keep the resolved column's bucket separate) and at completion. `findWithIdentifier(idMap, columnId)` translates the source column id through the accumulating map.

**Probe:** no unit test upstream. Source-grounded probe: `import.service.ts:2620-2630` (header index discovery) vs `:2637-2698` (known-bucket push vs first-sight resolve+flush) and `:2706-2714` (complete flush + return).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "importLinkFromCsvStream lChunks mmColumns handledLinks findWithIdentifier", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt lazy mm-column resolution with per-junction chunk buckets, flush-on-first-sight, and a threaded handledLinks dedup list; adapt the row wire format and bucket flush trigger to host. Omit the CSV specifics if you pass structured link batches. Coverage caveat: no in-repo tests; source-grounded.
