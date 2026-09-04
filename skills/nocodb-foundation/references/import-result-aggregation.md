<!-- capsule-v2 -->
|# DataImport processor — sample-error extraction over per-table import results

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How does the DataImport JOB layer report failure when the streaming pipeline is swallow-and-continue by design?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/data-import/data-import.processor.ts:DataImportProcessor` (~35–280); timing at :179 + :265–271; producer `services/data-import.service.ts:103`.

**Signature:** `job(job)` aggregates `results: {errors: {..., error?}[]}[]` — one entry per imported table.

**Data Shape:** each table result carries row-level error objects (`error` present = failed op with typed cause). Processor flattens across tables for the FIRST sample error (one log line) while returning full results through the job value.

### Decisive source
```ts
const sampleError = results
  .flatMap((r) => r.errors)
  .find((e) => e?.error)?.error;

elapsedTime(hrTime,
  `${importType.toUpperCase()} import completed for ${results.length} table(s)`, 'fileImport');
log(...);
```

**Flow:** payload → initTime → delegate to the streaming pipeline (AsyncQueue backpressure, error ladder, link phases — all in service capsules) → collect per-table results → flatMap+find a representative error → split-log → return structured outcome. Row-retry vs system-abort classification happened INSIDE the service; the processor only samples.

**Invariant:** (1) Sample-don't-stream at the job boundary: one representative error for logs, FULL list via job result for UI. (2) Per-table isolation holds to the top — sibling tables never abort. (3) Whole-run timing as ONE lap; finer phases belong to the service. (4) `importType.toUpperCase()` keeps human log channels uniform without per-format branches.

**Probe:** no unit test upstream. Source-grounded probe: processor :261-266 (flatMap/find chain verbatim), :265-271 (timing + log), data-import.service.ts:103 (producer).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DataImportProcessor sampleError flatMap fileImport elapsedTime", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt first-sample error reporting with full-results-through-job-value and per-table isolation; adapt shapes; omit format parsing (service capsules own it). Coverage caveat: no in-repo unit tests; source-grounded.
