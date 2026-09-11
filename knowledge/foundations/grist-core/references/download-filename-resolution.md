<!-- capsule-v2 -->
# Download filename resolution & empty-query default — how does grist name exported files, and why does /download/xlsx treat an empty query string specially?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the title-vs-docname precedence for download filenames, and what is the legacy behavior encoded in DocApi's xlsx route?

## Query title wins; else docTitle[-tableId]; xlsx defaults ONLY when query is truly empty
**Path/Symbol:** `app/server/lib/DocApi.ts` — `_getDownloadFilename(req, tableId?, optDoc?)` (:1760–1770), `_getDownloadOptions(req, doc?)` (:1772–1777), xlsx route empty-query branch :1284–1289, `parseExportParameters` (Export.ts:118–136).
**Signature:** `_getDownloadFilename(req: Request, tableId?: string, optDoc?: Document): Promise<string>`.
**Data Shape:** `title` arrives as a QUERY param (`optStringParam(req.query.title, "title")`); doc metadata comes from HomeDBManager `getDoc` unless the caller already fetched it (the `optDoc` pass-through avoids a duplicate round-trip on routes that need `doc` anyway, e.g. table-schema :1247).

### Decisive source
```ts
// DocApi.ts:1760-1770
private async _getDownloadFilename(req: Request, tableId?: string, optDoc?: Document): Promise<string> {
    let filename = optStringParam(req.query.title, "title");
    if (!filename) {
      // Query DB for doc metadata to get the doc data.
      const doc = optDoc || await this._dbManager.getDoc(req);
      const docTitle = doc.name;
      const suffix = tableId ? (tableId === docTitle ? "" : `-${tableId}`) : "";
      filename = docTitle + suffix || "document";
    }
    return filename;
}
// DocApi.ts:1284-1290 — the ONLY format with a no-parameter default path
const options: DownloadOptions = (!_.isEmpty(req.query) && !_.isEqual(Object.keys(req.query), ["title"])) ?
      await this._getDownloadOptions(req) :
      {
        filename: await this._getDownloadFilename(req),
        header: "label",
      };
await downloadXLSX(activeDoc, req, res, options);
```

**Invariant:** (1) Precedence: explicit `?title=` beats everything; else `docName` plus `-tableId` suffix SUPPRESSED when identical to the doc title (no `Foo-Foo.xlsx`); literal fallback `"document"` covers falsy concatenation. (2) The xlsx branch condition encodes history: an EMPTY query (or exactly `?title=x`) means "whole-doc export with label headers" — any OTHER parameter (viewSection/tableId/filters…) routes through full option parsing. This keeps ancient bookmarked URLs working while parameterized exports gain view-section fidelity. CSV/TSV have NO such default — they always parse options and require a tableId/viewSection downstream (400 otherwise). (3) `_getDownloadOptions` = `parseExportParameters` (validated query params incl. header∈{label,colId}) + resolved filename — one object shape (`DownloadOptions`) feeds every format handler.

**Flow:** each `/download/*` route → `_getDownloadOptions` (or xlsx default branch) → `downloadDSV/downloadXLSX/collectTableSchemaInFrictionlessFormat` → handlers append extensions (`.csv/.tsv/.dsv/.xlsx`) onto this base filename before content-disposition.

**Probe:** deterministic greps:
```bash
cd $REFERENCE_ROOT/grist-core
grep -n '_getDownloadFilename' app/server/lib/DocApi.ts | head -2       # 416, 666 (+def 1760)
grep -n 'docTitle + suffix || "document";' app/server/lib/DocApi.ts     # 1768
grep -n '!_.isEqual(Object.keys(req.query), \["title"\])' app/server/lib/DocApi.ts  # 1285
grep -n 'header: "label",' app/server/lib/DocApi.ts                     # 1287
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "download filename title docId options", limit: 5 });
// → resolves DocApi region nodes (BM25 noise floor caveat; _getDownload* are class-private methods cited by range)
```

## Verdict
Adopt title-over-docname-with-suffix-suppression verbatim for multi-artifact downloads from one entity. The empty-query compatibility branch is a pattern to recognize rather than copy: when you add parameters to a legacy endpoint, decide EXPLICITLY which old URLs must keep working and encode that boundary in one predicate, as grist did here.
