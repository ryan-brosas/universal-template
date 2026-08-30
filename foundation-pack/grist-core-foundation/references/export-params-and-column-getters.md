<!-- capsule-v2 -->
# Export parameter parsing + ServerColumnGetters — how do query params become a typed export request, and how do row accessors resolve cells by column REF?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the exact query-string contract for exports, and what is the rowId→value resolution machinery both sort and filter layers share?

## optJsonParam-driven options object + dual-map getter kernel
**Path/Symbol:** `app/server/lib/Export.ts` — `parseExportParameters` (:118–136) over `optStringParam`/`optIntegerParam`/`optJsonParam` from `app/server/lib/requestUtils`; `ServerColumnGetters` (`app/server/lib/ServerColumnGetters.ts`, whole file 72L); Sort helpers `Sort.getColRef` (app/common/SortSpec.ts:128) / `Sort.swapColRef` (:212–218).
**Signature:** `parseExportParameters(req): ExportParameters { tableId?, viewSectionId?, sortOrder?: number[], filters: Filter[], linkingFilter, header? }`; `new ServerColumnGetters(rowIds: number[], dataByColId: BulkColValues, columns: any[])`.
**Data Shape:** wire names differ from field names — `req.query.activeSortSpec` → `sortOrder`, `req.query.viewSection` → `viewSectionId`; `filters`/`linkingFilter` arrive as JSON arrays in the query string. Getters keep TWO maps: `_rowIndices: Map<rowId, array-index>` and `_colIndices: Map<colRef, colId>`.

### Decisive source
```ts
export function parseExportParameters(req: express.Request): ExportParameters {
  const tableId = optStringParam(req.query.tableId, "tableId");
  const viewSectionId = optIntegerParam(req.query.viewSection, "viewSection");
  const sortOrder = optJsonParam(req.query.activeSortSpec, []) as number[];
  const filters: Filter[] = optJsonParam(req.query.filters, []);
  const linkingFilter: FilterColValues = optJsonParam(req.query.linkingFilter, null);
  const header = optStringParam(
    req.query.header, "header", { allowed: ["label", "colId"] },
  ) as ExportHeader | undefined;
  ...
}
```
```ts
public getColGetterByColId(colId: string): ColumnGetter | null {
  if (colId === "id") {
    return (rowId: number) => rowId;              // synthetic identity column
  }
  const col = this._dataByColId[colId];
  if (!col) return null;
  return (rowId: number) => {
    const idx = this._rowIndices.get(rowId);
    if (idx === undefined) return null;           // unknown row → null, never throw
  };
}
```
**Invariant:** ALL list-shaped parameters ride as JSON inside the query string via `optJsonParam` with safe defaults (`[]`, `null`) — there is no body on a GET download, so complex filters must serialize into the URL; the `header` param is allowlist-validated at parse time (`{allowed:["label","colId"]}`), making downstream `col[colPropertyAsHeader]` indexing injection-safe. The getter returns NULL getters for unknown columns (sort layer tolerates missing columns by design — doExportSection's spec rewrite already dropped dead refs to `0`), and `null` VALUES for unknown rows rather than throwing. `"id"` is synthesized on demand since raw data chunks don't carry it. `getManualSortGetter` finds the `manualSort` column by convention name so views can sort by drag order.

**Flow:** route handler calls `parseExportParameters(req)` once (DocApi.ts:1773) → options flow through `downloadDSV`/`streamXLSX` → miners build `ServerColumnGetters(rowIds, dataByColId, columns)` from ONE fetched table chunk → `getters.getColGetter(col.id)` per projected column ref → the SAME getters feed `SortFunc` (compare), `buildRowFilter` predicates, and final cell accessors — one construction, three consumers. Choice-order sorting hooks in here too: `details.orderByChoice` wraps the getter with `choiceGetter(getter, choices)` when the column is a Choice (:37–44).

**Probe:** deterministic greps:
```bash
cd /mnt/hdd/utopia/inspo/grist-core
grep -n 'allowed: \["label", "colId"\]' app/server/lib/Export.ts    # 125
grep -n "req.query.activeSortSpec" app/server/lib/Export.ts         # 121
grep -n "return (rowId: number) => rowId;" app/server/lib/ServerColumnGetters.ts  # 58
grep -rn "parseExportParameters(req)" app/server/lib/DocApi.ts      # 1773
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "doExportSection", limit: 5 });
// ServerColumnGetters is consumed at Export.ts:368 within doExportSection 291-397;
// parseExportParameters resolves via search_code "parseExportParameters" DocApi.ts line-exact.
```

## Verdict
Adopt the GET-download contract verbatim for read-only exports: JSON-in-query for structured params with explicit defaults, allowlisted enums validated at the boundary, one typed options object flowing everywhere. Adopt ServerColumnGetters whenever you need rowId-addressed columnar access shared across sort/filter/render — the two-map (rowId→index, colRef→colId) design is what keeps O(1) per-cell lookups while tolerating missing columns gracefully. Omit nothing from the null-ladder: returning null-getter/null-value instead of throwing is what lets stale sort specs and racing edits degrade quietly during long downloads.
