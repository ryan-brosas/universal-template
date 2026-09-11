<!-- capsule-v2 -->
# ExcelFormatter typed-cell dialect — how does XLSX export produce real Excel types instead of strings, and how do moment formats become numFmt codes?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** Which grist types map to which JavaScript values per cell, what does `formatAny` do on wrong-typed cells, and what is the token-mapping contract between moment format strings and Excel number formats?

## Native-value registry: numbers stay numbers, dates become Date objects, everything else stringifies
**Path/Symbol:** `app/server/lib/ExcelFormatter.ts` whole file (265L) — `BaseFormatter` (:20–94) with `formatAny` gate (:91–93) and ExcelJS style builder `style()` (:38–85), formatter registry (:159–172), factory `createExcelFormatter` (:179–182), `DateFormatter` timezone handling (:124–148), moment→numFmt token map (:195–232) + chunked converter `excelDateFormat` (:239–265).
**Signature:** `createExcelFormatter(type: string, opts: FormatOptions): BaseFormatter`; per-cell `formatAny(value: any): any`.
**Data Shape:** registry keys are BARE grist types (after `extractTypeFromColType`, so `"DateTime:America/New_York"` → `"DateTime"`); style options come from column widgetOpts (`fillColor`/`textColor`/`alignment`/`dateFormat`/`timeFormat`/`numMode`/`currency`).

### Decisive source
```ts
const formatters: Partial<Record<GristType, typeof BaseFormatter>> = {
  // for numbers - return javascript number
  Numeric: NumberFormatter,
  Int: NumberFormatter,
  // for booleans - return javascript booleans
  Bool: BaseFormatter,
  // for dates - return javascript Date object
  Date: DateFormatter,
  DateTime: DateTimeFormatter,
  ChoiceList: ChoiceListFormatter,
  // for attachments - return blank cell
  Attachments: UnsupportedFormatter,
  // for anything else - return string (use default AnyFormatter)
};

public formatAny(value: any): any {
  return this.isRightType(value) ? this.format(value) : formatUnknown(value);
}
```
**Invariant:** the VALUE returned decides the Excel cell type (exceljs maps JS primitives to spreadsheet types), so each formatter's job is to emit the right PRIMITIVE — `Number.isFinite(value) ? value : ""` (non-finite numbers must NOT reach exceljs as NaN), `time.toDate()` after `moment(value*1000).tz(zone).utc(true).local()` (grist stores seconds-since-epoch; the utc(true)-then-local dance keeps wall-clock time stable across zones), booleans pass through untouched, attachments render as blank cells. Wrong-typed cells fall to shared `formatUnknown` stringification rather than crashing. DateFormatter OVERRIDES `isRightType` to `typeof value === "number"` because a raw Date-formatted column can legitimately hold non-date sentinels.

**Flow:** worker's `convertToExcel` builds ONE `createExcelFormatter(col.formatter.type, col.formatter.widgetOpts)` per column (workerExporter.ts:225) and calls `formatAny(getter(row))` per cell — note it re-derives from `formatter.type` (the full colType incl. `:` suffixes) while the registry lookup extracts the bare type again. `style()` converts widget cosmetics into column-level ExcelJS styles; currency numFmt embeds the symbol via `getSymbolFromCurrency(currency ?? "")` with `$` final fallback (`"${currencySymbol} "#,##0.000`). `excelDateFormat` splits on separators `([\s:.,-/]+)`, maps every TOKEN through the table, and fails closed on the FIRST unknown chunk to the passed default — custom formats degrade wholesale, never partially.

**Probe:** deterministic greps (coverage caveat: no dedicated unit file):
```bash
cd $REFERENCE_ROOT/grist-core
grep -n "Attachments: UnsupportedFormatter" app/server/lib/ExcelFormatter.ts   # 170
grep -n "return this.isRightType(value) ? this.format(value) : formatUnknown(value)" app/server/lib/ExcelFormatter.ts  # 92
grep -n "time.utc(true).local()" app/server/lib/ExcelFormatter.ts              # 145
grep -c "mapping.set(" app/server/lib/ExcelFormatter.ts                        # 33 tokens
```
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "createExcelFormatter BaseFormatter style", limit: 5 });
// → grist-core.app.server.lib.ExcelFormatter.createExcelFormatter Function app/server/lib/ExcelFormatter.ts 179-182
```

## Verdict
Adopt whenever exporting to a TYPED target (xlsx, parquet, SQL): keep a per-type registry of primitive-emitting formatters, route every cell through an isRightType gate with a shared unknown-value fallback, and translate your display-format strings to native format codes via a fail-closed token map. Adapt the registry to your type system. Omit the timezone dance only if your storage is already zone-aware — but if you store epoch seconds like grist, the utc(true).local() trick is the difference between correct and shifted exports.
