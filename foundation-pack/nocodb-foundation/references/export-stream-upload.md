<!-- capsule-v2 -->
# Concurrent stream export — how does a job write to storage while still streaming data into it, so a 10 GB export never sits in memory or on local disk?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the export job overlap producer (query→stream) and consumer (storage upload) without either blocking the other?

## pump-and-upload race with error capture
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-export/data-export.processor.ts:DataExportProcessor.job` (30-270); same pattern in `export-import/duplicate.processor.ts:importModelsData` (1029-1088).
**Signature:** `job(job: Job<DataExportJobData>): Promise<{url, title, type, ...}>`; streams: `dataStream = new Readable({read() {}})`.
**Data Shape:** destPath `nc/uploads/data-export/<YYYY-MM-DD>/<HH>/<modelId>/<filename>.<ext>`; result url = presigned (3 h expiry).

### Decisive source
```ts
const uploadFilePromise = (storageAdapter as any)
  .fileCreateByStream(destPath, encodedStream)
  .catch((e) => { this.logger.error(e); error = e; });     // consumer starts FIRST

this.exportService.streamModelDataAsCsv(context, { dataStream, ... })
  .catch((e) => { dataStream.push(null); error = e; });    // producer pumps concurrently

url = await uploadFilePromise;   // join point: wait for upload to finish
if (error) { throw error; }      // then surface the captured producer/consumer error
```

**Flow:** start the storage upload promise (it consumes the Readable), THEN start the exporter which pushes rows into it — both run concurrently on the event loop. Producer error ⇒ `push(null)` ends the stream so the upload finalizes a truncated-but-valid file, and `error` is rethrown after the join. No await between pump and upload.
**Invariant:** never `await` the producer before starting the upload — Node buffers would grow unbounded. The error variable is captured by BOTH sides and thrown only after `await uploadFilePromise`, because throwing early would leak an unfinished upload handle. Excel gets no `setEncoding('utf8')` (binary output).
**Probe:** no unit test upstream. Source-grounded probe: `data-export.processor.ts:124-129` vs `:188-207` — two `.catch` handlers assigning the shared `error`, single `await uploadFilePromise; if (error) throw` join at `:209-213`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "fileCreateByStream streamModelDataAsCsv uploadFilePromise", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt concurrent pump/upload with post-join error surfacing and push(null)-on-producer-error; adapt storage adapter calls, path scheme, and presign TTL to host; omit format-specific mimetype mapping. Coverage caveat: no in-repo tests; source-grounded.
