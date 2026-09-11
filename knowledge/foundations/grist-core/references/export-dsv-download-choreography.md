<!-- capsule-v2 -->
# DSV download choreography — how does grist turn export data into a CSV/TSV/DSV HTTP response, and why is the poop emoji a delimiter?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the section-vs-table branch structure, the delimiter→(extension, MIME type) mapping, and the exact matrix assembly that feeds node-csv?

## One entrypoint, two sources, three delimiters — headers chosen per request
**Path/Symbol:** `app/server/lib/ExportDSV.ts` whole file (183L) — entrypoint `downloadDSV` (:25–49), `makeDSVFromViewSection` (:68–90), `makeDSVFromTable` (:104–126), matrix builder `convertToDsv` (:133–146), `Delimiter = "," | "\t" | "💩"` (:19) with extension map `getDSVFileExtension` (:150–162) and MIME map `getDSVMimeType` (:171–183); route callers `DocApi.ts:1268/1274/1280`.
**Signature:** `downloadDSV(activeDoc: ActiveDoc, req: express.Request, res: express.Response, options: DownloadDsvOptions)` where `DownloadDsvOptions extends DownloadOptions { delimiter: Delimiter }`.
**Data Shape:** `csvMatrix: string[][]` — row 0 = header cells (`col[colPropertyAsHeader]`, default property `"label"`, request may force `"colId"`), then one row per rowId of `formatters[c].formatAny(getter(row))` strings; `stringifyAsync(csvMatrix, { delimiter })` from node-csv does all quoting/escaping.

### Decisive source
```ts
type Delimiter = "," | "\t" | "💩";
...
const colPropertyAsHeader = header ?? "label";
const csvMatrix = [viewColumns.map(col => col[colPropertyAsHeader])];
// populate all the rows with values as strings
rowIds.forEach((row) => {
  csvMatrix.push(access.map((getter, c) => formatters[c].formatAny(getter(row))));
});
return stringifyAsync(csvMatrix, { delimiter });
```
```ts
case "💩": {
  return ".dsv";                       // extension map
}
...
"text/x-doo-separated-values";         // MIME map, "not a registered MIME type, hence x-"
```
**Invariant:** ALL cell values are stringified by the shared ValueFormatter chain (`formatAny`) before node-csv sees them — DSV has no typed cells, so formatting happens at projection time and quoting is entirely delegated to `stringifyAsync`. The `"💩"` delimiter is real product surface (DocApi.ts:1280 wires it to an endpoint): `.dsv` files use an unguessable separator so spreadsheets can't auto-mangle the columns; the MIME `text/x-doo-separated-values` is deliberately unregistered. Branch rule: `viewSectionId ? makeDSVFromViewSection : tableId required else ApiError("tableId parameter is required", 400)` (:35–45). Response framing: `Content-Type` from delimiter map, `Content-Disposition` via the `content-disposition` package (`filename + extension`) — never hand-build that header.

**Flow:** options destructure → branch → both paths end in `convertToDsv(data, {header, delimiter})`; the table path additionally guards `activeDoc.docData` presence and resolves `_grist_Tables.findRow("tableId")` with `tableRef === 0 → ApiError(...404)`. Formatters come from `ExportColumn.formatter` (built in doExportTable/doExportSection), so CSV and XLSX share ONE format decision tree up to the dialect split.

**Probe:** deterministic greps (coverage caveat: no dedicated unit file):
```bash
cd $REFERENCE_ROOT/grist-core
grep -cF '"💩"' app/server/lib/ExportDSV.ts        # 3 (type union + 2 switch arms)
grep -n "text/x-doo-separated-values" app/server/lib/ExportDSV.ts   # 169, 180
grep -n "delimiter: \",\"" app/server/lib/DocApi.ts # 1268 (route pins delimiter per endpoint)
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "downloadDSV delimiter getDSVMimeType", limit: 5 });
// → grist-core.app.server.lib.ExportDSV.downloadDSV Function app/server/lib/ExportDSV.ts 25-49
```

## Verdict
Adopt for any tabular HTTP download: single entrypoint branching on section vs table id, one string-matrix builder shared by all delimited formats, delimiter as a closed type with paired extension/MIME maps, and framework-built Content-Disposition. The emoji-delimiter trick is worth adapting wherever machine-readability matters more than spreadsheet-friendliness. Omit nothing from the maps — adding a delimiter without BOTH switch arms compiles in TS exhaustiveness only if the union is closed; keep it closed.
