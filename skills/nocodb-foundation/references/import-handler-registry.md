<!-- capsule-v2 -->
# Import handler registry — how do CSV/JSON/Excel parsers plug into one import pipeline through a two-method interface?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What contract must a new file-format handler satisfy?

## DataImportHandler preview/streamRows registry
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/handlers/data-import-handler.interface.ts:DataImportHandler` (whole); registry `handlers/index.ts:getImportHandler`.
**Signature:** `preview(readStream, parserConfig): Promise<ImportPreviewSheet[]>`; `streamRows(readStream, parserConfig, columns, sheetName?): AsyncGenerator<ImportRow>`; `getImportHandler(importType): DataImportHandler` (throws on unknown).
**Data Shape:** CSV/JSON → exactly one sheet per file; Excel → one per worksheet (`sheetName` selects); `ImportPreviewSheet = {columns, previewData, totalSampleRows, totalRows, detectedDelimiter?}`.

### Decisive source
```ts
const handlers: Record<string, DataImportHandler> = {
  csv: new CsvImportHandler(),
  json: new JsonImportHandler(),
  excel: new ExcelImportHandler(),
};
export function getImportHandler(importType: string): DataImportHandler {
  const handler = handlers[importType];
  if (!handler) NcError.badRequest(`Unsupported import type: ${importType}`);
  return handler;
}
```

**Flow:** the controller path calls `preview()` for schema proposals and row samples before import; `streamSheetData` later calls `streamRows()` with the user-confirmed columns and target sheet. Both methods consume a fresh Readable of the same attachment (see import-attachment-stream).
**Invariant:** streamRows must be an async generator (backpressure via consumer pull — see import-streaming), NOT a callback API. Unknown type must throw a badRequest naming the offender — silent fallback would import nothing and report success. Sheet multiplicity is the only format difference the pipeline knows about.
**Probe:** no unit test upstream. Source-grounded probe: interface doc comment "CSV/JSON produce exactly one sheet per file; Excel produces one per worksheet"; registry guard at `handlers/index.ts:12-17`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "DataImportHandler getImportHandler streamRows preview", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-method parser interface + eager registry map; adapt preview schema to your UI; omit Excel sheet semantics if single-sheet only. Coverage caveat: no in-repo tests; source-grounded.
