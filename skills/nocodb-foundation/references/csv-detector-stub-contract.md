<!-- capsule-v2 -->
# CSV/JSON type-detector stub contract — what do the import handlers actually get back from detectColumnTypes, and which of its heuristics are dead?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** When a CSV/JSON/Excel import creates columns, where does type detection really happen — and what would a porter get catastrophically wrong by "restoring" the obvious-looking logic?

## Deliberate no-op entry points over orphaned heuristics
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/data-import/csv-type-detector.ts` (whole file, 240L) — public `detectColumnTypes(headers, _sampleRows, _options)` (:210-222), public `detectColumnTypesFromObjects(headers, _sampleRows, _options)` (:228-240), shared `initializeColumns` (:172-205); dead-below-the-line helpers `_detectInitialUidt` (:144-149, ZERO callers repo-wide), `isCheckboxType` (:32-47), `getCheckboxValue` (:49-51), `isMultiLineTextType` (:53-60), `isEmailType` (:62-67), `isUrlType` (:69-74), `isDecimalType` (:76-78), `extractMultiOrSingleSelectProps` (:80-141) — none imported anywhere else (`grep -rn` across `src/` confirms only the three handlers import the two public fns).
**Signature:** `detectColumnTypes(headers: string[], sampleRows: string[][], options?: {maxRowsToParse?: number; autoSelectFieldTypes?: boolean}): DetectedColumn[]`; same for the FromObjects variant with `Record<string, any>[]` rows.
**Data Shape:** `DetectedColumn = {title, column_name, ref_column_name, uidt, key, meta, dtxp?}`; every returned column has `uidt: UITypes.SingleLineText`, `meta: {}`, and no `dtxp`.

### Decisive source
```ts
export function detectColumnTypes(headers, _sampleRows,
  _options: { maxRowsToParse?; autoSelectFieldTypes? } = {}): DetectedColumn[] {
  const columns = initializeColumns(headers);
  // Skip column type detection — all columns default to SingleLineText
  return columns;
}
// initializeColumns: sanitize + dedupe only
let cn = sanitizeColumnName(columnName, `field_${columnIdx + 1}`);
while (cn in columnNamePrefixRef) { cn = `${cn}${++columnNamePrefixRef[cn]}`; }
while (title in titlePrefixRef)   { title = `${title}${++titlePrefixRef[title]}`; }
columnNamePrefixRef[cn] = 0; titlePrefixRef[title] = 0;
```

**Flow:** csv/json/excel handlers each parse a bounded sample (`maxRowsToParse`, default 500 in excel) and call their variant with `autoSelectFieldTypes` defaulting to true — the flag is accepted and ignored. The detector returns sanitized/deduped name triples only; every column lands as SingleLineText. The underscore prefix on `_sampleRows`/`_options` is the codebase's own signal that the params are deliberately unused, not an unfinished migration someone should "finish".
**Invariant:** the two public functions are the ONLY live surface. Everything below them looks like a full heuristic engine (checkbox option pairs incl. `[x]`/`☑`/`✅`, email regex, URL validation, >255-char multiline, decimal-vs-int, select-option extraction with the ≤64-options cap and the `uniqueVals <= ceil(total/2)` multi-select ratio test) but is unreachable dead code kept in-file. A porter who "helpfully" wires `_detectInitialUidt`/`extractMultiOrSingleSelectProps` back in changes product behavior: imports that today create plain text columns would start coercing types, splitting select options on commas, and rewriting dtxp — silently diverging from upstream. The dedupe counters are seeded `{ id: 0, Id: 0 }` so a literal `id` header is renamed (e.g. `id1`) rather than colliding with the reserved pk.
**Probe:** no unit test upstream. Deterministic probe: `grep -rn "_detectInitialUidt\|extractMultiOrSingleSelectProps" packages/nocodb/src --include='*.ts' | grep -v csv-type-detector.ts` → empty (orphans confirmed at f7513664); handler call sites `csv-import.handler.ts:79`, `json-import.handler.ts:226`, `excel-import.handler.ts:121` all pass through to the stub bodies.
**Coverage caveat:** file indexed clean (no parse_partial ranges); claims are grep + whole-file read, not test-derived.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "detectColumnTypes DetectedColumn initializeColumns SingleLineText", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the stub contract as-is when porting quick-import flows: sanitize names, dedupe against reserved prefixes, ship SingleLineText, and let users retype columns afterwards. Omit the heuristic graveyard below the line (or mine it as optional reference for a user-facing auto-detect feature) — never reconnect it to these entry points. Adapt `DetectedColumn` field names to your schema layer.
