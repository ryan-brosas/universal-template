<!-- capsule-v2 -->
# exportBase fan-out — per-table data streams + one merged link stream, uploaded concurrently with error capture across the join

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How does a whole-source export write schema.json plus one CSV per table and a single links.csv — without one table's failure corrupting the rest?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.exportBase` (2231–2363).

**Signature:** `exportBase(context, {path, sourceId}): Promise<{path}>` — writes under `export/{baseId}/{sourceId}/{path}/` via the storage plugin.

**Data Shape:** artifacts: `schema.json` (single JSON push: `{id: '{base}::{source}', models: serializedModels}`), `data/{model.id}.csv` per non-mm table (streamed), `data/links.csv` (all junctions merged). Shared mutable state: ONE `handledMmList: string[]` threaded through every `streamModelDataAsCsv` call so a junction is streamed exactly once repo-wide; per-model `error` capture var.

### Decisive source
```ts
const models = (await source.getModels(context)).filter(m => m.source_id === source.id && !m.mm && m.type === 'table');
const handledMmList: string[] = [];
// links.csv upload starts BEFORE any producer runs
const uploadLinkPromise = storageAdapter.fileCreateByStream(`${destPath}/data/links.csv`, combinedLinkStream);
for (const model of models) {
  const dataStream = new Readable({ read() {} }); const linkStream = new Readable({ read() {} });
  const linkPromise = new Promise(resolve => {          // tee this model's link chunks into the merged stream
    linkStream.on('data', chunk => combinedLinkStream.push(chunk));
    linkStream.on('end',   () => { combinedLinkStream.push('\r\n'); resolve(null); });
    linkStream.on('error', e  => { debugLog(e); resolve(null); });      // error resolves, never rejects
  });
  const uploadPromise = storageAdapter.fileCreateByStream(`${destPath}/data/${model.id}.csv`, dataStream);
  let error = null;
  this.streamModelDataAsCsv(context, { dataStream, linkStream, baseId: base.id, modelId: model.id, handledMmList })
      .catch(e => { debugLog(e); dataStream.push(null); linkStream.push(null); error = e; });
  await Promise.all([uploadPromise, linkPromise]);
  if (error) throw error;                                // AFTER both streams drained
}
combinedLinkStream.push(null); await uploadLinkPromise;
```

**Flow:** serializeModels → schema.json upload → loop per table: create streams → start uploads → start pump (not awaited) → await BOTH the data upload and the link-tee promise → rethrow captured pump errors only after streams closed. The merged link stream ends once after the loop; its own upload was started first so backpressure never deadlocks.

**Invariant:** pump errors must close BOTH streams and be rethrown only after `Promise.all` — throwing earlier abandons open uploads. Link-stream errors RESOLVE (not reject) their promise: one bad table's links must not kill the whole export. `handledMmList` is shared deliberately — two tables linked by the same junction stream it once, and the `\r\n` separator between models' link blocks matches what the importer's papaparse step expects. The mm-table exclusion (`!m.mm`) prevents junction rows appearing as data CSVs.

**Probe:** no unit test upstream. Source-grounded probe: `export.service.ts:2243-2246` (filter incl. `!m.mm` + TODO cache comment), `:2288-2295` (early link-upload start), `:2306-2320` (tee + resolve-on-error), `:2327-2344` (error capture → post-join throw — mirrors the export-stream-upload pattern at file scope).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "exportBase fileCreateByStream handledMmList combinedLinkStream", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt per-entity artifact streaming with an early-started shared sink, tee-and-resolve side channels, shared dedup lists, and post-join error rethrow; adapt paths/adapters to host; omit schema.json shape unless porting full migration. Coverage caveat: no in-repo unit tests; source-grounded.
