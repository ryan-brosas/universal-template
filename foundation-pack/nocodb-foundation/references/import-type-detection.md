<!-- capsule-v2 -->
# Import sampling & type-detection boundary — what evidence do handlers collect for column creation, and what does the detector do with it today?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How do CSV/JSON/Excel handlers sample data before table creation, and where does type inference actually happen?

## Capped string-sample collection → deliberate no-op detector
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/handlers/csv-import.handler.ts` — parserConfig defaults (:20-25), header/sample split (:27-54), detector call (:79-82), preview mapping (:84-90); `handlers/json-import.handler.ts:226`, `handlers/excel-import.handler.ts:121` — same call via `detectColumnTypesFromObjects`; `csv-type-detector.ts:detectColumnTypes/detectColumnTypesFromObjects` (:210-240) — STUB BODIES returning all-SingleLineText columns (full dead-heuristic inventory: csv-detector-stub-contract.md).
**Signature:** `detectColumnTypes(headers: string[], sampleRows: string[][], {maxRowsToParse = 500, autoSelectFieldTypes = true}): DetectedColumn[]`.
**Data Shape:** sample capped at maxRowsToParse (500); per column `{title, column_name, ref_column_name, uidt:'SingleLineText', key, meta}`; preview returns first 20 rows keyed by detected column names.

### Decisive source
```ts
// handler side — sampling contract feeding the detector:
if (rowCount === 1 && firstRowAsHeaders) {
  headers.push(...row.data);            // first row never enters the sample
} else {
  if (rowCount === 1) for (let i = 0; i < row.data.length; i++) headers.push(`Field ${i + 1}`);
  if (sampleRows.length < maxRowsToParse) sampleRows.push(row.data);
}
...
const columns = detectColumnTypes(headers, sampleRows, { maxRowsToParse, autoSelectFieldTypes });
// DETECTOR SIDE (current truth at f7513664):
const columns = initializeColumns(headers);
// Skip column type detection — all columns default to SingleLineText
return columns;
```

**Flow:** papaparse steps through the file once; the header row is peeled off (or synthesized as `Field N` when `firstRowAsHeaders:false`), and up to 500 data rows accumulate as strings-only evidence alongside the auto-detected delimiter. The evidence is then handed to a detector that — at this pin — IGNORES it beyond name sanitation/deduping: every column ships as SingleLineText with no dtxp. The three handlers (CSV via string rows; JSON/Excel via object rows) share this exact boundary; excel's `autoSelectFieldTypes` default is likewise accepted and unused.
**Invariant:** (1) detection runs on STRINGS from parse-time, not coerced values — any future inference must see original cell text. (2) The sample cap bounds memory on multi-GB files; only the first 20 sample rows feed previewData. (3) `autoSelectFieldTypes=false` is TODAY a semantic no-op (columns are text either way); historically it yielded all-text columns for user override — porters wiring real detection must honor it. (4) Header synthesis must not shift column indices (`Field ${i+1}` positional). (5) DO NOT "restore" the heuristic ladder below the stub entry points — see csv-detector-stub-contract.md for why that changes product behavior.
**Correction note:** earlier revision described a live per-column candidate ladder (number→decimal→date→checkbox). That ladder exists only as DEAD code below the stub entry points at f7513664 (`_detectInitialUidt` has zero callers repo-wide). Source wins.
**Probe:** no unit test upstream. Deterministic probes: `csv-import.handler.ts:31-56` — header/sample split with cap; `:79-82` — call site; `csv-type-detector.ts:220-221,238-239` — literal skip comments in both stub bodies; `grep -rn "_detectInitialUidt" packages/nocodb/src --include='*.ts' | grep -v csv-type-detector.ts` → empty.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "detectColumnTypes detectColumnTypesFromObjects maxRowsToParse sampleRows initializeColumns", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the capped-string-sample boundary and positional header synthesis for streaming imports; treat the detector seam as an extension point (collect now, classify later) rather than a feature to backfill from the graveyard. Adapt the sample cap and preview window to your UX; omit delimiter sniffing if your parser doesn't expose it. Coverage caveat: no in-repo tests; source-grounded whole-file read.
