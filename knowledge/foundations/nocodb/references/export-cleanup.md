<!-- capsule-v2 -->
# Date-folder cleanup job — how do you garbage-collect time-partitioned uploads by parsing the partition key out of the path instead of listing metadata?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does the cleanup job delete expired exports using only the date embedded in each file path?

## scan-stream + PQueue(1) + path-date cutoff
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-export-clean-up/data-export-clean-up.processor.ts:DataExportCleanUpProcessor.job` (12-108).
**Signature:** `job(job: Job): Promise<boolean>` (resolves after `queue.onIdle()`).
**Data Shape:** files under `nc/uploads/data-export/YYYY-MM-DD/HH/...`; cutoff = now − 4 h formatted `YYYY-MM-DD`; stats `{scannedCount, deletedCount, errorCount}`.

### Decisive source
```ts
const queue = new PQueue({ concurrency: 1 });
const fileStream = await storageAdapter.scanFiles('nc/uploads/data-export/**');
fileStream.on('data', (filePath) => {
  queue.add(async () => {
    const pathParts = filePath.split('/');
    const dateIndex = pathParts.indexOf('data-export') + 1;
    const folderDate = pathParts[dateIndex];
    if (folderDate && folderDate < cutoffDateFormatted) {   // lexicographic date compare
      await storageAdapter.fileDelete(filePath);
    }
  }).catch((err) => { errorCount++; });                     // never rethrow into queue
});
fileStream.on('end', async () => { await queue.onIdle(); resolve(true); });
```

**Flow:** storage adapter streams every export path; each becomes a queued delete task (concurrency 1 — gentle on the object store); a file dies iff its `YYYY-MM-DD` folder segment sorts before the cutoff string. The hour subfolder is intentionally ignored: retention is day-granular even though writes are hour-partitioned.
**Invariant:** ISO dates compare correctly as strings — no Date parsing. Individual task failures must be caught at the `.catch` of `queue.add(...)`, not inside-then-rethrow, or one unreadable object kills the whole scan. Resolve waits for `onIdle()`, guaranteeing all deletes complete before the job reports success.
**Probe:** no unit test upstream. Source-grounded probe: `data-export-clean-up.processor.ts:64-71` — the string `<` on folderDate vs cutoffDateFormatted; `:88-103` — end handler awaits onIdle before resolve.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DataExportCleanUpProcessor scanFiles PQueue onIdle", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt path-partition-key GC with lexicographic date compare and serialized deletes; adapt prefix, retention window, and glob to host; omit moment/dayjs choice. Coverage caveat: no in-repo tests; source-grounded.
