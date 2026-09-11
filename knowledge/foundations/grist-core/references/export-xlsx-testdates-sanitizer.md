<!-- capsule-v2 -->
# XLSX testDates sentinel + worksheet sanitizer — how do grist's Excel tests get byte-stable output and safe sheet names?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** How is XLSX output made deterministic for testing, and which characters must be stripped from sheet names?

## Hostname sentinel freezes workbook metadata; regex ladder tames table names
**Path/Symbol:** sentinel: `app/server/lib/ExportXLSX.ts` :48 `const testDates = (req.hostname === "localhost");` → plumbed through `exportPool.run({..., testDates, ...})` :78 → consumed `app/server/lib/workerExporter.ts` `convertToExcel` :187–195. Sanitizer: `sanitizeWorksheetName(tableName)` (workerExporter.ts:266–277), applied at :223.
**Signature:** `sanitizeWorksheetName(tableName: string): string`; testDates flows as a plain boolean argument (part of the MessagePort-serializable task payload).
**Data Shape:** ExcelJS `wb.modified/created/lastPrinted` timestamps + `creator/lastModifiedBy` strings are embedded in the xlsx zip; sheet names max 31 chars, invalid chars `* ? : / \ [ ]`.

### Decisive source
```ts
// ExportXLSX.ts:48 — the ONLY trigger is hostname; no env var, no query flag
const testDates = (req.hostname === "localhost");
// workerExporter.ts:187-195 — frozen metadata makes binary output reproducible
if (testDates) {
    // HACK: for testing, we will keep static dates
    const date = new Date(Date.UTC(2018, 11, 1, 0, 0, 0));
    wb.modified = date;
    wb.created = date;
    wb.lastPrinted = date;
    wb.creator = "test";
    wb.lastModifiedBy = "test";
}
// workerExporter.ts:263-277 — exported for reuse/tests
/**
 * Removes invalid characters, see https://github.com/exceljs/exceljs/pull/1484
 */
export function sanitizeWorksheetName(tableName: string): string {
  return tableName
    // Convert invalid characters to spaces
    .replace(/[*?:/\\[\]]/g, " ")
    // Collapse multiple spaces into one
    .replace(/\s+/g, " ")
    // Trim spaces and single quotes from the ends
    .replace(/^['\s]+/, "")
    .replace(/['\s]+$/, "");
}
```

**Invariant:** (1) Determinism is scoped to HOSTNAME, not environment — only localhost requests get frozen metadata, so production bytes still carry real timestamps while any dev/test machine reproduces them. The sentinel travels with the TASK (not global state) so pooled threads stay stateless. (2) Sanitizer ordering matters: invalid→space FIRST (so `a/b` → `a b` not `ab`), THEN collapse whitespace, THEN trim quotes+spaces from both ends — reordering would leave doubled spaces or quote-leading names. Single quotes are trimmed only at ENDS because mid-name apostrophes are legal ("John's sheet"). Note it does NOT truncate to 31 chars — grist table ids in practice fit; a porter targeting strict Excel limits must add truncation themselves. (3) Styles are on (`useStyles:true, useSharedStrings:true`, :184) to match historical output; row commits stream per-row via `maybeCommit` (:250–252) keeping memory flat.

**Flow:** route `_getDownloadOptions` → `downloadXLSX` → `streamXLSX` stamps `testDates=req.hostname==="localhost"` → worker `convertToExcel(stream, testDates, {header})` applies frozen metadata + per-table `addWorksheet(sanitizeWorksheetName(tableName))`.

**Probe:** deterministic greps:
```bash
cd $REFERENCE_ROOT/grist-core
grep -n 'req.hostname === "localhost"' app/server/lib/ExportXLSX.ts  # 48
grep -n 'Date.UTC(2018, 11, 1' app/server/lib/workerExporter.ts      # 189
grep -n 'useStyles: true, useSharedStrings: true' app/server/lib/workerExporter.ts  # 184
grep -c 'maybeCommit(ws.addRow' app/server/lib/workerExporter.ts     # 1
grep -n 'column.width = column.header.length < 14 ? 14 : column.header.length;' app/server/lib/workerExporter.ts  # 246
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "sanitizeWorksheetName convertToExcel worksheet header style", limit: 4 });
// → sanitizeWorksheetName Function 266-277 rank#1 line-exact; convertToExcel 174-261
```

## Verdict
Adopt the hostname-scoped determinism sentinel for ANY binary artifact generated over HTTP where tests compare bytes (xlsx/pdf/zip) — cheaper and safer than env-var plumbing, self-documenting at the route layer. Adopt the sanitizer verbatim as the minimal ExcelJS-compliant name cleaner; add length truncation per your constraints and document the divergence.
