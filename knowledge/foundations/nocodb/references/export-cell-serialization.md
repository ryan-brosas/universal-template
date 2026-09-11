<!-- capsule-v2 -->
# Export cell serialization & CSV formula-escape — how are raw DB cells normalized into export shape, and how does a user-facing CSV avoid CWE-1236 spreadsheet formula injection?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What per-cell normalization does a CSV export apply, and how is the formula-injection guard (CWE-1236) scoped so it never corrupts numeric/temporal data?

## per-uidt cell normalization + scoped formula escaping
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.streamModelDataAsCsv` `formatData` (1034–1131) + `unparseExportRows` (1992–2006); `packages/nocodb/src/helpers/csvFormulaEscape.ts` (whole, 75L).
**Signature:** `formatData(data): {data}` mutates each row in place; `escapeFormulaeInRows(rows, columns): void`; `escapeFormulaHeader(titles): string[]`; `escapeCsvFormulaValue(value): unknown`.
**Data Shape:** rows keyed by column TITLE (serialized export shape); `NC_FORMULA_TRIGGER_RE = /^[=+\-@\t\r]/`; `NC_FORMULA_ESCAPE_SKIP_UITYPES` = Number/Decimal/Currency/Percent/Rating/Duration/Year/Date/DateTime/Time/Checkbox/AutoNumber/ID.

### Decisive source
```ts
switch (col.uidt) {
  case UITypes.ForeignKey: if (btMap.has(col.id)) { row[btMap.get(col.id)] = v; delete row[k]; } break;
  case UITypes.Attachment: row[colId] = (typeof v === 'string') ? (isJson(v) ? v : null) : JSON.stringify(v); break;
  case UITypes.LongText:   row[colId] = col.meta?.[LongTextAiMetaProp] && v ? JSON.stringify(v) : v; break;
  case UITypes.User/CreatedBy/LastModifiedBy:
    if (param.excludeUsers) { row[colId] = null; break; }
    row[colId] = (v ? (Array.isArray(v) ? v : [v]).map(u => u.email).join(',') : v); break;
  case UITypes.Formula/Lookup/Button/Rollup/Barcode/QrCode: skip = true; break;  // never exported
  case UITypes.JSON: row[colId] = tryJsonStringify(v) ?? null; break;
  default: row[colId] = v; break;
}
if (v === '') row[colId] = '__nc_empty_string__';   // preserve explicit empty string
```
```ts
// csvFormulaEscape.ts — CWE-1236 guard, applied ONLY to user-facing CSV exports
export function escapeFormulaeInRows(rows, columns) {
  const skipTitles = new Set(columns.filter(c => c.uidt && NC_FORMULA_ESCAPE_SKIP_UITYPES.has(c.uidt)).map(c => c.title));
  for (const row of rows) for (const k of Object.keys(row))
    if (!skipTitles.has(k)) row[k] = escapeCsvFormulaValue(row[k]);   // prefix ' if /^[=+\-@\t\r]/
}
```

**Flow:** raw cells are normalized per uidt (FK→btMap rewrite, attachment JSON, user→comma-joined emails, formula/lookup/rollup dropped, JSON stringified). Explicit empty strings are preserved as the `__nc_empty_string__` sentinel (the importer maps it back to `''`). For user-facing exports (`dataExportMode`), every cell and the header row are pushed through the formula-escape guard — a leading `= + - @ tab CR` gets a single-quote prefix so Excel/Sheets treats it as text. Numeric/temporal columns are skipped because a real negative/signed value legitimately leads with `-`/`+`.

**Invariant:** the escape is applied ONLY to user-facing CSV exports, NOT to the duplicate/migrate/re-import CSV path (which reads values back verbatim — escaping would corrupt the round-trip). The header is escaped too (a title is equally user-controlled and has NO skip-set, since titles are always text labels). `unparseExportRows` uses the `{fields, data}` form when escaping the header so the escaped keys don't break value lookup.

**Probe:** no unit test upstream. Source-grounded probe: `export.service.ts:1034-1131` (formatData uidt switch) + `:1992-2006` (unparseExportRows) vs `csvFormulaEscape.ts:32-75` (escape functions + skip-set).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "escapeFormulaeInRows escapeFormulaHeader NC_FORMULA_ESCAPE_SKIP_UITYPES formatData", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt per-uidt cell normalization with the `__nc_empty_string__` sentinel, and the CWE-1236 formula-escape guard scoped to text cells + header on user-facing exports only; adapt the skip-uidt set and trigger regex to host. Omit the attachment/user serialization specifics unless porting those column types. Coverage caveat: no in-repo tests; source-grounded.
