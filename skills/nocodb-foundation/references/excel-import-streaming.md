<!-- capsule-v2 -->
# Excel streaming import — how do you read huge workbooks sheet-by-sheet without loading them, and what does each cell value actually arrive as?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f75113664f3f3`; Codebase Memory project `nocodb`. **Question:** What reader options and cell-value unwrapping make streamed XLSX importable, and how do you select one sheet safely?

## WorkbookReader options + resolveCellValue union ladder
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/handlers/excel-import.handler.ts` — WORKBOOK_READER_OPTIONS (:14-19), `resolveCellValue` (:26-48), header synthesis incl. `Field N` gap-fill (:93-104), streamRows non-target-sheet drain (:154-163), early return after target sheet (:178).
**Signature:** `new ExcelJS.stream.xlsx.WorkbookReader(readStream, {entries:'emit', sharedStrings:'cache', styles:'ignore', hyperlinks:'ignore'})`; iterate worksheets via `for await (const ws of workbookReader)`, rows via `for await (const row of ws)`; cells via `row.eachCell({includeEmpty: true}, (cell, colNumber) => …)`.
**Data Shape:** cell value is a tagged UNION — `{richText:[{text}]}` | `{formula, result}` | `{hyperlink, text}` | `{error}` | Date | primitive; resolved to plain string/number/null.

### Decisive source
```ts
function resolveCellValue(cell: ExcelJS.Cell): any {
  const value = cell.value;
  if (value === null || value === undefined) return null;
  if ('richText' in value)  return value.richText.map((rt) => rt.text).join('');
  if ('formula' in value)   return value.result ?? null;   // cached result, never the formula
  if ('hyperlink' in value) return value.text ?? null;     // display text, not the URL
  if ('error' in value)     return null;                   // #REF! etc → null
  if (value instanceof Date) return value.toISOString();   // normalize before column typing
  return value;
}
// streamRows: Drain non-target sheets so exceljs doesn't stall the stream.
if (sheetName && ws.name !== sheetName) { for await (const _row of ws) {} continue; }
```

**Flow:** preview iterates EVERY worksheet, synthesizing headers from row 1 (`Field N` fills gaps for empty/sparse header cells), sampling ≤ maxRowsToParse rows into the shared type detector → streamRows maps confirmed columns by their 1-based `key` index, drains every non-selected sheet to completion (exceljs requires full consumption or downstream iteration stalls), yields rows only from the named sheet and returns right after it.
**Invariant:** you must unwrap the cell-value union BEFORE type detection — a raw `{formula}` object would become a JSON-blob column. `includeEmpty: true` keeps column INDICES stable: skipping empties renumbers colNumber and silently shifts data under the wrong headers. Draining skipped sheets is not optional cleanup; it is how the stream stays alive. Dates are normalized to ISO at the boundary so CSV/JSON/Excel handlers converge on identical values.
**Probe:** no unit test upstream. Source-grounded probe: options object pins styles/hyperlinks to 'ignore' (:14-19) proving minimal-parse intent; drain comment :157; `if (sheetName) return` :178 stops reading after the target sheet.
**Coverage caveat:** no in-repo tests; source-grounded.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "ExcelImportHandler resolveCellValue WorksheetReader eachCell includeEmpty", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the union-unwrapping ladder + mandatory-drain pattern for any streaming XLSX read; adapt reader options to your memory budget; omit multi-sheet selection if single-sheet-only.
