<!-- capsule-v2 -->
# Download route map & option parsing funnel — how do grist's five /download endpoints share one parameter grammar?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Where is the single place export parameters are parsed/validated, and how does each format endpoint compose with it?

## parseExportParameters is the only query-grammar owner; routes differ only in handler + delimiter
**Path/Symbol:** parser `app/server/lib/Export.ts` `parseExportParameters(req)` (:118–136); routes `app/server/lib/DocApi.ts` :1245 (`download/table-schema`), :1265 (`csv`), :1271 (`tsv`), :1277 (`dsv`), :1283 (`xlsx`), :1293 (`send-to-drive`); options assembly `_getDownloadOptions` :1772–1777.
**Signature:** `parseExportParameters(req): ExportParameters` = `{tableId?, viewSectionId?, sortOrder?, filters?, linkingFilter?, header?}`; `header` validated `{allowed: ["label", "colId"]}`.
**Data Shape:** all params arrive as QUERY STRING (not body): `activeSortSpec` and `filters`/`linkingFilter` are JSON-encoded via `optJsonParam`; `viewSection` is an integer param named without the "Id".

### Decisive source
```ts
// Export.ts:118-136
export function parseExportParameters(req: express.Request): ExportParameters {
  const tableId = optStringParam(req.query.tableId, "tableId");
  const viewSectionId = optIntegerParam(req.query.viewSection, "viewSection");
  const sortOrder = optJsonParam(req.query.activeSortSpec, []) as number[];
  const filters: Filter[] = optJsonParam(req.query.filters, []);
  const linkingFilter: FilterColValues = optJsonParam(req.query.linkingFilter, null);
  const header = optStringParam(
    req.query.header, "header", { allowed: ["label", "colId"] },
  ) as ExportHeader | undefined;
  return { tableId, viewSectionId, sortOrder, filters, linkingFilter, header };
}
// DocApi.ts:1265-1281 — three text formats, one handler, delimiter is the only delta
this._app.get("/api/docs/:docId/download/csv", canView, withDoc(async (activeDoc, req, res) => {
      const options = await this._getDownloadOptions(req);
      await downloadDSV(activeDoc, req, res, { ...options, delimiter: "," });
}));
// ... tsv -> "\t" (:1274) ... dsv -> "💩" (:1280)
```

**Invariant:** (1) EVERY download route funnels through `_getDownloadOptions` → `parseExportParameters`, so validation errors (bad header value, non-integer viewSection, malformed JSON filter specs) throw identically across formats — a porter adding a new format MUST reuse this funnel rather than re-parse. (2) Dispatch between table/section/whole-doc happens INSIDE handlers by presence of `viewSectionId` vs `tableId` (both absent on XLSX = whole doc; both absent on DSV = 400 via `!tableId` guard ExportDSV.ts:41–43) — the parser itself never rejects that combination. (3) All routes sit behind `canView` + `withDoc` middleware; send-to-drive adds `decodeGoogleToken`. (4) Because params are query-string based, exports are plain GET links — shareable/bookmarkable, cache-friendly, and CSRF-safe in the same way as any GET (auth still enforced by middleware).

**Flow:** browser/app builds `/api/docs/:id/download/csv?viewSection=12&activeSortSpec=[...]&filters=[...]` → DocApi route → options funnel → format handler → Export.ts spine (see export-section-filter-sort-spine) → response headers from the format capsule family.

**Probe:** deterministic greps:
```bash
cd $REFERENCE_ROOT/grist-core
grep -c 'await this._getDownloadOptions(req' app/server/lib/DocApi.ts   # 5 routes use the funnel
grep -n 'export function parseExportParameters' app/server/lib/Export.ts  # 118
grep -n 'allowed: \["label", "colId"\]' app/server/lib/Export.ts           # 125
grep -n '/api/docs/:docId/download/' app/server/lib/DocApi.ts              # 5 route lines (:1245/:1265/:1271/:1277/:1283); send-to-drive :1293
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "parseExportParameters download options request", limit: 5 });
// → resolves Export.parseExportParameters Function node line-exact (BM25 noise floor caveat for DocApi-private helpers)
```

## Verdict
Adopt the single-funnel grammar for any multi-format export API: one parser owns names/types/validation; format routes add ONLY their dialect constants. Adopt query-string GET semantics deliberately (shareable export URLs); switch to POST bodies only when filter specs exceed URL limits — and then keep the same parser on the decoded body.
