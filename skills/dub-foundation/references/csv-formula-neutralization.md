<!-- capsule-v2 -->
# CSV formula neutralization — spreadsheet-safe exports at the serialization boundary

**Source:** dub AGPL-3.0-or-later main@29df217a29631ced4041882a28d2327cc4546f27; Codebase Memory dub. **Question:** Where is the single choke point that stops user-controlled strings (=, +, -, @, tab, CR, LF) from executing as spreadsheet formulas when an exported CSV opens in Excel?

## json2csv parseValue hook + FORMULA_PREFIXES apostrophe guard
**Path/Symbol:** apps/web/lib/analytics/utils/convert-to-csv.ts:convertToCSV (:10-28), neutralizeCsvFormula (:6-8), FORMULA_PREFIXES (:3).
**Signature:** convertToCSV(data: object[]) -> string; neutralizeCsvFormula(value: string) -> string.
**Data Shape:** arbitrary hydrated export rows (objects); every leaf field passes through parseValue(fieldValue, defaultParser).

### Decisive source
```ts
const FORMULA_PREFIXES = new Set(["=", "+", "-", "@", "\t", "\r", "\n"]);

// Prevents CSV/Excel formula injection
function neutralizeCsvFormula(value: string): string {
  return FORMULA_PREFIXES.has(value[0] ?? "") ? APOS + value : value;   // source: ? `'${value}` : value  (apostrophe prefix)
}

export const convertToCSV = (data: object[]) => {
  return json2csv(data, {
    parseValue(fieldValue, defaultParser) {
      if (fieldValue == null) return "";
      if (fieldValue instanceof Date) return fieldValue.toISOString();
      if (typeof fieldValue === "string") return defaultParser(neutralizeCsvFormula(fieldValue));
      return defaultParser(fieldValue);
    },
  });
};
```
(convert-to-csv.ts whole file, 28 lines)

**Flow:** any exporter (events columns, top_* breakdowns, payout exports) -> convertToCSV -> per field: null to empty string, Date to ISO string, strings prefixed with an apostrophe when the FIRST character is one of =+-@ or tab/CR/LF -> default parser quotes/escapes the rest.
**Invariant:** neutralization lives INSIDE the serializer, not per caller — no export path can forget it. Only string fields are touched (negative numbers stay numeric because the typeof gate excludes them). The value[0] ?? empty-string guard makes empty strings safe without throwing.
**Probe:** executed at pin: grep -n FORMULA_PREFIXES convert-to-csv.ts -> :3,:7 (definition + guard). Related row projection apps/web/lib/analytics/events-export-helpers.ts:eventsExportColumnAccessors (:19-40): _root keys render bare domain (:23), countries map through COUNTRIES with raw-code fallback (:24-25), customer renders name plus email angle-bracket form (:28-29), saleAmount formats cents+currency via formatMoneyCentsForExport (:31-38). Coverage caveat: no dedicated unit test for convert-to-csv under tests/analytics — behavior anchored by whole-file source read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "dub", file_pattern: "convert-to-csv", limit: 10 });
// rank-1 observed: convert-to-csv.convertToCSV Function 10-28 (+ neutralizeCsvFormula 6-8, FORMULA_PREFIXES 3-3)
```

## Verdict
Adopt the serializer-level parseValue hook and the exact six-prefix set. Adapt the prefix character (apostrophe is the Excel convention). Omit nothing — small enough to port verbatim.