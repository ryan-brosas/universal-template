<!-- capsule-v2 -->
# Attachment migration — how do you backfill FileReference rows for millions of legacy storage files and re-point cell JSON at them, resumably?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What is the scan→ledger→per-model→per-cell pipeline, and which three invariants keep it restartable?

## Scan ledger + offset ledger + PQueue model fan-out
**Path/Symbol:** `packages/nocodb/src/modules/jobs/migration-jobs/nc_job_001_attachment.ts:job` (:24-601) — stream pause/resume ingest (:85-135), end-of-stream error surfacing (:137-162), per-model external-source SELECT 1 gate (:209-230), cell rewrite + offset persist (:280-465), model discovery loop (:540-587).
**Signature:** two temp tables — `nc_temp_file_references(file_path PK-idx, mimetype, referenced, thumbnail_generated)` and `nc_temp_processed_models(fk_model_id, offset, completed)`; `processModel` walks `baseModel.list({limit: 50, sort: pks})` until an empty page.
**Data Shape:** cell value = JSON array or JSON string of attachments `{url?, path?, id?, size, mimetype,…}`; after migration every entry carries a real `id` from `FileReference.insert`.

### Decisive source
```ts
fileScanStream.on('data', async (file) => {
  fileReferenceBuffer.push({ file_path: file });
  if (fileReferenceBuffer.length >= 100) {
    fileScanStream.pause();
    const processBuffer = fileReferenceBuffer.splice(0, fileReferenceBuffer.length);
    const toSkip = await ncMeta.knexConnection(temp_file_references_table)
      .whereIn('file_path', processBuffer.map((f) => f.file_path));   // dedup vs earlier runs
    // bulk insert of the remainder … err captured, NOT thrown here
    fileScanStream.resume();                                          // swap-before-await
  }
});
// only AFTER 'end': throw the captured async insert errors
await new Promise((res, rej) => { stream.on('end', res); stream.on('error', rej); });
await Promise.all(insertPromises);
if (err) throw err;
```

**Flow:** create-if-missing both ledgers → scan storage under `nc/uploads/**` into the reference ledger with pause/resume batches of 100 → discover models having Attachment columns via a COLUMNS meta-scan minus completed models → PQueue(2) over models; each model: resolve source/model/baseModel, gate external sources behind a 10s `SELECT 1` race, page 50 rows by PK sort → per attachment cell: parse-or-skip malformed JSON, extractProps to the 9-field whitelist, map `path`/`url` to `nc/uploads/...` key, mark ledger row referenced, upsert root-scope FileReference (`deleted:true` tombstone) when missing, then either reuse the cell's existing `attachment.id` (verifying it exists) or mint one and REWRITE the cell JSON with PKs re-attached → persist `offset` after EVERY page → completed=true.
**Invariant:** (1) errors thrown inside the async 'data' handler cannot reject the stream await — capture-and-resurface-after-end or the job "succeeds" on a partial scan; (2) the offset must be persisted before processing the NEXT page, not after the loop — that IS the resume cursor; (3) path normalization strips the `download/` prefix because read-key ≠ write-key (matches thumbnail-processor-path-algebra). Skip-on-missing-source/model keeps one dead base from killing the fleet run.
**Probe:** no unit test upstream. Source-grounded probe: pause/resume bracket :89/:133; late-throw :153-156; 10s timeout race :214-219; offset update inside while(true) at :461-464 BEFORE loop continues.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "AttachmentMigration processModel temp_file_references dataOffset extractProps", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-ledger shape for any storage-vs-meta reconciliation backfill; adapt batch sizes; omit the external-source liveness gate if you only own local storage.
