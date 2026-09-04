<!-- capsule-v2 -->
|# Export-cleanup job lifecycle — stream-scan → serialized deletes, and the dormant-producer caveat

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** The export-cleanup capsule covers date-folder GC mechanics — how does the cleanup JOB consume the storage adapter, and what must a porter know before wiring it?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/data-export-clean-up/data-export-clean-up.processor.ts:job` (12–109); producer state `redis/jobs.service.ts:33-42` + `fallback/jobs.service.ts:20-27` (both COMMENTED OUT).

**Signature:** `job(job: Job): Promise<boolean>` (resolves true via wrapped Promise).

**Data Shape:** scans `nc/uploads/data-export/**`; grammar `.../data-export/YYYY-MM-DD/<HH>/...` — the date segment is found by `indexOf('data-export') + 1`, NOT a fixed index. Cutoff = `moment().subtract(4,'hours')` formatted YYYY-MM-DD, compared lexicographically against the folder string. Stats: scanned/deleted/error counters.

### Decisive source
```ts
const queue = new PQueue({ concurrency: 1 });            // serialized deletes
const fileStream = await storageAdapter.scanFiles(globPattern);
return new Promise((resolve, reject) => {
  fileStream.on('data', (filePath) => {
    queue.add(async () => {
      if (folderDate && folderDate < cutoffDateFormatted) {   // lexicographic day compare
        await storageAdapter.fileDelete(filePath);
      }
    }).catch((err) => { errorCount++; /* don't stop the scan */ });
  });
  fileStream.on('end', async () => { await queue.onIdle(); resolve(true); });
});
```

**Flow:** adapter scan stream → per-file enqueue into concurrency-1 PQueue → prefix guard (`startsWith('nc/uploads/data-export')`) → segment-search date parse → delete-if-older → resolve after onIdle.

**Invariant:** (1) Scan and delete run CONCURRENTLY but deletes are serialized — adapter-safe ordering without blocking the scan. (2) Per-file failure is swallow-and-count; only stream-level 'error' rejects. (3) Subtract-4h-then-format means "today" survives until tomorrow: DAY-STRING comparison makes subtracted hours matter only near midnight (deliberately coarse vs attachment-orphan-gc's DB retention windows). (4) **LIFECYCLE CAVEAT:** no live producer in this tree (see repeat-job-registration-gap.md) — adopt requires wiring your own scheduler; the portable part is scan-stream→serial-delete-queue.

**Probe:** no unit test upstream. Source-grounded probe: processor :15 (concurrency 1), :56-64 (segment-search extraction), :77 ("Don't rethrow to prevent queue from stopping"), :88-103 (onIdle resolve), jobs-map.service.ts:76-78 (registered-but-dormant).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DataExportCleanUpProcessor scanFiles fileDelete onIdle", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt scan-stream→serialized-delete-queue and segment-search parsing; adapt glob/cutoff to host policy; omit unless you also wire a producer (upstream ships it disabled). Coverage caveat: no in-repo unit tests; source-grounded.
