<!-- capsule-v2 -->
# Data-import streaming pipeline — how do CSV/JSON/Excel rows flow from file to bulk-insert without loading the file into memory, and how does the parser not outrun the database?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How do parsed rows flow into batched bulk inserts under backpressure?

## handler → AsyncQueue → for-await → flush ladder
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/data-import.processor.ts:DataImportProcessor.streamSheetData` (646-926); `packages/nocodb/src/modules/jobs/jobs/data-import/handlers/async-queue.ts:AsyncQueue` (whole); `handlers/csv-import.handler.ts:CsvImportHandler.streamRows`.
**Signature:** `streamRows(readStream, parserConfig, columns, sheetName?): AsyncGenerator<ImportRow>`; `AsyncQueue.push(value, resume)` / `.end()` / `.error(err)`.
**Data Shape:** BATCH_SIZE=1000 rows/insert; per-row `{destCn: coercedValue}`; LTAR cells split into `[colId, values[]]` intents carried parallel to each row (`batchLtar`).

### Decisive source
```ts
// AsyncQueue: producer's resume() is held until the consumer iterates again
yield item.value;
item.resume();            // ← papaparse's parser.resume() — backpressure point

// consumer side:
for await (const sourceRow of handler.streamRows(readStream, parserConfig, spec.columns ?? [], spec.sheetName)) {
  const dbRow = {};       // map source col → dest col + type coercion
  ...
  batch.push(dbRow); batchLtar.push(rowLtar); processedRows++;
  if (batch.length >= BATCH_SIZE) { await flush(); reportProgress();
    if (!hasSelfRefLink && pendingLinkRows >= linkFlushThreshold) await flushLinks(); }
}
await flush();            // drain remainder
await flushLinks();
```

**Flow:** papaparse step-callback pushes `(row, resume)` into AsyncQueue and pauses the parser; the generator yields; only after the consumer takes the next iteration is `parser.resume()` invoked. Consumer maps/coerces each row, batches to 1000, flushes via `bulkDataService.bulkDataInsert(..., skip_hooks: true, raw: true)`, then optionally drains link intents.
**Invariant:** exactly one resume per pushed row — drop it and the parser stalls forever; call it early and memory balloons. The flush swaps `batch` synchronously before awaiting (`const pending = batch; batch = []`) so late rows land in the next batch, never double-inserted. Excel date serials are converted ONLY for excel+number+date-column inputs in `coerceValue`; CSV/JSON date strings pass through untouched.
**Probe:** no unit test upstream. Source-grounded probe: `async-queue.ts` asyncIterator — `resume()` strictly after `yield`; `data-import.processor.ts:786-791` — swap-before-await in `flush()`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "AsyncQueue streamRows streamSheetData bulk insert", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt callback-parser→AsyncQueue→async-generator bridging with held-resume backpressure, 1000-row swap-before-await flushes, and hooks-off raw inserts; adapt batch size, coercion rules, and service names to host; omit Excel-specific serial conversion unless importing workbooks. Coverage caveat: no in-repo tests; source-grounded.
