<!-- capsule-v2 -->
# Recursive paged stream — how do CSV/JSON exports page a DB table into a Readable stream with correct framing, headers, and termination?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** How does a large table stream to CSV/JSON without loading it all, keeping headers/array-framing correct and pushing `null` exactly once?

## offset/limit recursion over a Readable
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.recursiveRead` (2026–2163) + `recursiveReadForJson` (1891–1968) + `recursiveLinkRead` (2165–2229).
**Signature:** `recursiveRead(context, formatter, baseModel, stream, model, view, offset, limit, fields, header, delimiter, dataExportMode, param?): Promise<void>`; `recursiveReadForJson(..., isFirst, param?): Promise<void>`; `recursiveLinkRead(..., header): Promise<boolean>`.
**Data Shape:** pages of `limit=200` via `datasService.dataList`; `result.pageInfo.isLastPage` gates recursion; `buildNestedLinkLimitQuery` raises LTAR nested limits to `defaultLimitConfig.limitMax`.

### Decisive source
```ts
// CSV: header on first page only; '\r\n' separator between pages; null exactly once at last page
if (!header) stream.push('\r\n');
const formatterPromise = formatter(result.list);
formatterPromise.then(({ data }) => {
  if (dataExportMode) escapeFormulaeInRows(data, model.columns);
  stream.push(this.unparseExportRows(data, { header, delimiter, escapeHeader: dataExportMode }));
  if (result.pageInfo.isLastPage) { stream.push(null); resolve(); }
  else this.recursiveRead(..., offset + limit, ..., /* header */ false, ...).then(resolve).catch(reject);
});
// Empty first page still emits a header row (so the consumer sees columns), then null.
if (result.list.length === 0 && offset === 0) { stream.push(unparse([titles], {header:true})); stream.push(null); resolve(); }
```
```ts
// JSON: open '[\n' on first page, ',\n' between non-first non-empty pages, '\n]' + null at last
if (isFirst) stream.push('[\n');
if (data.length > 0) { if (offset > 0) stream.push(',\n'); stream.push(data.map(r => JSON.stringify(r)).join(',\n')); }
if (result.pageInfo.isLastPage) { stream.push('\n]'); stream.push(null); }
else this.recursiveReadForJson(..., offset + limit, ..., false, param);
```

**Flow:** each call fetches one 200-row page, formats it, pushes the serialized chunk, and either terminates (`push(null)`) or recurses with `offset+limit`. The CSV variant writes the header only on the first page and a `\r\n` separator between pages; the JSON variant opens/closes the array bracket once and inserts `,` between batches. `recursiveLinkRead` (the mm side stream) additionally returns whether it WROTE any rows — an empty page must not spend the header, so it threads `header && !wrote` into the next recursion and ORs the wrote flags across pages.

**Invariant:** `push(null)` happens EXACTLY once, at the true last page — never mid-stream, or the consumer's `end` fires early. The CSV header must be emitted even for an empty first page (so the consumer sees the columns). For the link stream, a header is only claimed when at least one row was written — otherwise `unparse([])` yields `''` and a later junction would append headerless rows that papaparse then eats as a header. All recursion chains resolve/reject through the returned promise so errors propagate to the caller.

**Probe:** no unit test upstream. Source-grounded probe: `export.service.ts:2065-2080` (empty-first-page header) vs `:2101-2122` (isLastPage terminate vs recurse) and `:2191-2221` (recursiveLinkRead `wrote` threading).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "recursiveRead recursiveReadForJson recursiveLinkRead isLastPage push null", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt offset/limit recursion over a Readable with single `push(null)` termination, first-page-only headers, and wrote-aware header threading for side streams; adapt page size, separator, and JSON framing to host. Omit the LTAR nested-limit builder unless porting link exports. Coverage caveat: no in-repo tests; source-grounded.
