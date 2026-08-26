<!-- capsule-v2 -->
# Import progress reporting — what JSON does a long import emit so a UI can render live counters without scraping prose?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What is the machine-readable progress protocol inside the human-readable log stream?

## status:progress/completed JSON frames
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/data-import.processor.ts` — `reportProgress` (771-784), completion frame (272-284), per-column link log (1069-1077).
**Signature:** `reportProgress(): void` → `log(JSON.stringify({status:'progress', tableName, sheetName, rowsInserted, rowsFailed, totalProcessed}), true)`; final frame `{status:'completed', rowsInserted, rowsFailed, linksCreated, valuesUnmatched, linksFailed, errorsCount, sampleError?}`.
**Data Shape:** frames ride the SAME channel as prose lines (`jobsLogService.sendLog`); consumers distinguish by parsing leading `{`.

### Decisive source
```ts
const reportProgress = () =>
  log(JSON.stringify({
    status: 'progress',
    tableName: progressKey,
    sheetName: spec.sheetName,
    rowsInserted: stats.rowsInserted,
    rowsFailed: stats.rowsFailed,
    totalProcessed: processedRows,
  }), true);
...
log(JSON.stringify({ status: 'completed', rowsInserted, rowsFailed, linksCreated,
                     valuesUnmatched, linksFailed, errorsCount,
                     ...(sampleError ? { sampleError } : {}) }), true);
```

**Flow:** every BATCH_SIZE flush emits one progress frame; the run's end emits exactly one completed frame with cumulative counters and an optional sample error. Per-column link summaries stay prose (human context), while state transitions are always JSON — UIs parse only the frames.
**Invariant:** counters are CUMULATIVE across flushes (flushLinks adds via +=) — a UI must never diff consecutive frames to get totals. `tableName` uses `spec.tableName || tableName` because data-only imports may lack created titles. The completed frame must be emitted even when sheets fail (error path logs 'Import failed due to an internal error' separately).
**Probe:** no unit test upstream. Source-grounded probe: `data-import.processor.ts:273-284` vs `:775-783` — identical counter names between completed and progress frames.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "reportProgress status progress totalProcessed rowsInserted", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt typed JSON frames embedded in the log stream with stable cumulative field names; adapt frame schema to your UI; omit the prose mirrors. Coverage caveat: no in-repo tests; source-grounded.
