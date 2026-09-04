<!-- capsule-v2 -->
# CSV stream import with idMap header translation — how does a CSV data stream land in a destination table with source ids remapped and pg autoincrement realigned?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does `importDataFromCsvStream` translate source column headers through the idMap, bulk-insert in 1000-row chunks under papaparse backpressure, and fix pg sequences after verbatim-id inserts?

## papaparse step → header idMap → chunked bulk insert → pg sequence reset
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/export-import/import.service.ts:ImportService.importDataFromCsvStream` (2381–2562) + `resetPgAutoIncrementSequences` (2339–2379).
**Signature:** `importDataFromCsvStream(context, {idMap, dataStream, destProject, destBase, destModel, req, skipDuplicates?}): Promise<void>`.
**Data Shape:** `headers: (string|null)[]` resolved once from the first row via `idMap`; `chunk` accumulates up to 1000 rows; `dataHashSet: Set<string>` for `skipDuplicates` (object-hash of the row).

### Decisive source
```ts
papaparse.parse(dataStream, {
  newline: '\r\n',
  step: async (results, parser) => {
    if (!headers.length) {                       // first row = headers
      parser.pause();
      for (const header of results.data) {
        const id = idMap.get(header);            // source col id -> dest col id
        if (id) {
          const col = await Column.get(context, { source_id: destBase.id, colId: id });
          if (col?.colOptions?.type === BELONGS_TO || (ONE_TO_ONE && col.meta?.bt)) {
            const childCol = await Column.get(context, { source_id: destBase.id, colId: col.colOptions.fk_child_column_id });
            headers.push(childCol?.column_name ?? null);   // BT -> FK child column
          } else headers.push(col?.column_name ?? null);
        } else headers.push(null);                // unknown header -> dropped column
      }
      parser.resume();
    } else if (results.errors.length === 0) {
      const row = {};
      for (let i = 0; i < headers.length; i++) if (headers[i]) {
        if (results.data[i] !== '') row[headers[i]] = results.data[i] === '__nc_empty_string__' ? '' : results.data[i];
      }
      if (skipDuplicates) { const h = hash(row); if (!dataHashSet.has(h)) { dataHashSet.add(h); chunk.push(row); } }
      else chunk.push(row);
      if (chunk.length > 1000) {
        parser.pause();
        try { await this.bulkDataService.bulkDataInsert(context, { baseName: destProject.id, tableName: destModel.id, body: chunk, raw: true, undo: true, skipPermissionCheck: true, skipAttachmentOwnershipCheck: true, foreign_key_checks: !!destBase.isMeta() }); }
        catch (e) { parser.abort(); reject(e); return; }
        chunk = []; parser.resume();
      }
    }
  },
  complete: async () => { /* flush remainder */ await resetPgAutoIncrementSequences(...); resolve(null); },
});
```

**Flow:** the first parsed row is treated as headers and translated through the accumulating `idMap` (source column id → destination column), with BELONGS_TO link columns rewritten to their FK child column — the exact inverse of the export-side btMap. Unknown headers become `null` (column dropped, debug-logged). Data rows are mapped positionally, the `__nc_empty_string__` sentinel is restored to `''`, and rows batch into 1000-row chunks that pause papaparse, bulk-insert with `raw:true` + `undo:true` + permission/attachment-ownership checks skipped (import copies rows verbatim, not user edits), then resume. On `complete`, the remainder flushes and — because rows were inserted with their ORIGINAL ids (which does NOT advance a pg serial sequence) — `resetPgAutoIncrementSequences` realigns each autoincrement column to `MAX(id)` so the next user insert gets `MAX+1` instead of colliding.

**Invariant:** header translation happens exactly once (guarded by `!headers.length`), and only on a row with no papaparse errors. `parser.pause()` must bracket every `await` that could outrun the parser; `parser.abort()` on insert failure stops the stream and rejects. The pg sequence reset is best-effort (`try/catch` warn, never fails the import) and only runs for `source.type === 'pg'` on models with `ai` columns; an empty table leaves the sequence at its default. `skipDuplicates` uses object-hash of the whole row to drop already-seen rows.

**Probe:** no unit test upstream. Source-grounded probe: `import.service.ts:2411-2450` (header idMap translation + BT→FK child) vs `:2477-2513` (1000-row pause/insert/resume) and `:2339-2379` (resetPgAutoIncrementSequences).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "importDataFromCsvStream idMap headers bulkDataInsert resetPgAutoIncrementSequences", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt idMap header translation (with BT→FK child rewrite), pause/resume-bracketed chunked bulk insert, and post-import pg sequence realignment; adapt chunk size, hash function, and permission-skip policy to host. Omit the link side-stream (see import-link-stream capsule). Coverage caveat: no in-repo tests; source-grounded.
