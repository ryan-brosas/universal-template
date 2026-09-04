<!-- capsule-v2 -->
# JSON/Excel format variants — where the shared export pipeline forks: streaming array framing vs whole-buffer workbook assembly

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** The CSV path streams pages; what do the JSON and Excel variants change about field selection, ordering, memory, and formula-escape handling — and why does Excel skip CWE-1236 escaping?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.streamModelDataAsJson` (1305–1443), `streamModelDataAsExcel` (1674–1796), `recursiveReadForExcel` (1798–1889).

**Signature:** both take `{dataStream, baseId, modelId, viewId?, ncSiteUrl?, filterArrJson?, sortArrJson?, locale?}` (+`_fieldIds/excludeUsers/includeCrossBaseColumns` on JSON) over one `dataStream`; no linkStream in either variant.

**Data Shape:** JSON = text chunks `'[\n'`, per-page `JSON.stringify(row)` joined `',\n'`, `'\n]'`, then null. Excel = ONE binary buffer at last page (`XLSX.write({type:'buffer',bookType:'xlsx'})`) built from `allRows[]` accumulated across recursive calls with `headers[]` captured from page 0 keys.

### Decisive source
```ts
// JSON: view-visible fields ONLY (caller _fieldIds ignored for ordering), stream-framed
fields = viewCols.sort((a,b)=>a.order-b.order).filter(c=>c.show && !hideSystemFields.includes(c.fk_column_id))
                 .map(vc => model.columns.find(c=>c.id===vc.fk_column_id)?.title).filter(Boolean);
if (isFirst) stream.push('[\n');
if (data.length > 0) { if (offset > 0) stream.push(',\n'); stream.push(data.map(r=>JSON.stringify(r)).join(',\n')); }
if (result.pageInfo.isLastPage) { stream.push('\n]'); stream.push(null); }
else await this.recursiveReadForJson(..., offset+limit, ..., false, param);

// Excel: accumulate, then assemble ONCE; empty-first-page emits headers-only workbook
if (offset === 0 && data.length > 0) headers.push(...Object.keys(data[0]));
allRows.push(...data);
// No CWE-1236 escaping here, unlike CSV: json_to_sheet emits typed text cells
// (t:"s", no f), which spreadsheet apps never evaluate. Escaping would only corrupt.
const worksheet = XLSX.utils.json_to_sheet(allRows, { header: headers });
```

**Flow:** both resolve refView = passed view ?? first collaborative view, derive `fields` from VIEW column visibility/order (unlike CSV which honors caller `_fieldIds` order), serialize cells via the same `serializeCellValue` + viewOrder sort, then hand to a format-specific recursion. JSON frames incrementally (constant memory); Excel holds every formatted row and writes a single workbook buffer at isLastPage.

**Invariant:** Excel's recursion threads ACCUMULATORS (`allRows`, `headers`) as parameters through recursive calls instead of closing over them — porters who re-init them per call emit single-page workbooks. Empty-table behavior differs deliberately: JSON pushes literal `'[]'`; Excel builds a headers-only sheet from the `fields` list. The CWE-1236 asymmetry is a documented security/correctness trade-off: escape only where a formula bar can evaluate text (CSV), never where cells are typed strings.

**Probe:** no unit test upstream. Source-grounded probe: `export.service.ts:1367-1372` vs `:1724-1728` (identical view-derived fields), `:1924-1929` (JSON `'[]'` empty case) vs `:1832-1844` (Excel headers-only workbook), `:1849-1851` + `:1853` (accumulator threading), `:1856-1863` (the CWE-1236 comment verbatim).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "recursiveReadForExcel json_to_sheet book_append_sheet recursiveReadForJson", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt stream-framed JSON vs buffered-workbook Excel with accumulator-threading and the typed-cells-no-escape rule; adapt row/page limits to host; omit the `_fieldIds` JSON branch unless porting interface-scoped exports. Coverage caveat: no in-repo unit tests; source-grounded.
