<!-- capsule-v2 -->
# Frictionless schema export — how does grist emit a standards-compliant table schema, and what does each grist column type contribute beyond `type`?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the mapping from grist column types to Frictionless Table Schema fields (including locale-derived separators and boolean/choice constraints)?

## Type ladder with locale-aware number separators and per-type extras
**Path/Symbol:** `app/server/lib/ExportTableSchema.ts` whole file (138L) — entrypoint `collectTableSchemaInFrictionlessFormat` (:37–71), type mapper `buildTypeField` (:73–129), locale separator probe `getNumberSeparators` (:131–138); reuses the shared projection via `exportTable(activeDoc, tableRef, req)` (:59).
**Signature:** `collectTableSchemaInFrictionlessFormat(activeDoc: ActiveDoc, req: express.Request, options: DownloadOptions): Promise<FrictionlessFormat>`.
**Data Shape:** `FrictionlessFormat { name (kebab-cased tableId), title (tableName from primary view), schema.fields[] }`; each field = `{ name: col[header || "label"], description?, ...typeExtras }` where extras include `format`, `bareNumber`, `groupChar`, `decimalChar`, `gristFormat`, `constraints.enum`, `trueValue`/`falseValue`.

### Decisive source
```ts
function buildTypeField(col: ExportColumn, locale: string) {
  const type = col.type.split(":", 1)[0];          // strip widget suffixes BEFORE lookup
  const widgetOptions = col.formatter.widgetOpts;
  switch (type) {
    case "Text":
      return { type: "string", format: widgetOptions.widget === "HyperLink" ? "uri" : "default" };
    case "Numeric":
      return { type: "number", bareNumber: widgetOptions?.numMode === "decimal",
               ...getNumberSeparators(locale) };
    ...
    case "Bool":
      return { type: "boolean", trueValue: ["TRUE"], falseValue: ["FALSE"] };
    case "Choice":
      return { type: "string", constraints: { enum: widgetOptions?.choices } };
    case "ChoiceList":
      return { type: "array", constraints: { enum: widgetOptions?.choices } };
    case "Reference":
      return { type: "string" };                    // display value, not rowid
    default:
      return { type: "string" };
  }
}

function getNumberSeparators(locale: string) {
  const numberWithGroupAndDecimalSeparator = 1000.1;
  const parts = Intl.NumberFormat(locale).formatToParts(numberWithGroupAndDecimalSeparator);
  return {
    groupChar: parts.find(obj => obj.type === "group")?.value,
    decimalChar: parts.find(obj => obj.type === "decimal")?.value,
  };
}
```
**Invariant:** the sentinel `1000.1` is chosen so `formatToParts` yields BOTH a group and a decimal part — that's the whole trick for deriving separators without regex over formatted strings; it inherits the DOCUMENT's locale (`activeDoc.docData.docSettings().locale`), not the server's. The bare-type split must happen before the switch or `"DateTime:<tz>"`-style colTypes fall through to default-string. Reference columns export as plain strings because Frictionless has no reference concept — but they were already projected to DISPLAY values by doExportTable's substitution, so the schema stays honest about what the data file contains. Bool pins uppercase `TRUE`/`FALSE` tokens as the declared wire values.

**Flow:** guards (`docData` present, tableId given else 400, findRow else 404) → reuse `exportTable` for `{tableName, columns}` (identical visibility/display/formatting decisions as data exports — schema and data can never disagree) → fold each column through the header choice + description passthrough + `buildTypeField`. The DocApi route (`/download/table-schema`, DocApi.ts:1244–1262) then WRAPS the schema with a companion data contract — `{format:"csv", mediatype, encoding:"utf-8", path: <api>/download/csv?<same query>, dialect:{delimiter:",", doubleQuote:true}}` spread UNDER the schema fields — so consumers get schema + machine-readable pointer + CSV dialect in ONE response. Field name honors the same `header` option (`colId` vs `label`) as the data download, keeping schema and CSV headers aligned.

**Probe:** deterministic greps (coverage caveat: no dedicated unit file):
```bash
cd /mnt/hdd/utopia/inspo/grist-core
grep -n "1000.1" app/server/lib/ExportTableSchema.ts            # 132
grep -n 'split(":", 1)\[0\]' app/server/lib/ExportTableSchema.ts # 74
grep -n "trueValue" app/server/lib/ExportTableSchema.ts          # 109
grep -n "collectTableSchemaInFrictionlessFormat(activeDoc, req, options)" app/server/lib/DocApi.ts  # 1248 route
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "collectTableSchemaInFrictionlessFormat buildTypeField", limit: 5 });
// → buildTypeField Function app/server/lib/ExportTableSchema.ts 73-129 (+ entrypoint 37-71)
```

## Verdict
Adopt for any "export schema alongside data" feature (data dictionaries, dbt sources, data catalogs): reuse the SAME projection pipeline as the data path, then map types through an exhaustive switch with locale-derived separators via the formatToParts-sentinel trick. Adapt the target vocabulary (Frictionless here; JSON Schema/dbt elsewhere). Omit the HyperLink→uri refinement only if your text columns carry no URL semantics — but keep the bare-type normalization; suffix-bearing colTypes breaking the switch is the recurring porting bug.
