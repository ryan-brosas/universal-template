<!-- capsule-v2 -->
# Import column-metadata proposal — when should an imported column become empty-formula Any vs keep raw values?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** What metadata shape does the importer propose for all-empty and object-bearing columns, and how are widgetOptions serialized for user actions?

## guessColInfoForImports: all-empty ⇒ {type:"Any", isFormula:true}; any object ⇒ no proposal; widgetOptions JSON-stringified or DELETED
**Path/Symbol:** `app/common/ValueGuesser.ts`: `guessColInfoForImports` (:202–221) — empty rule :203–206, object veto :207–210, stringify-or-delete :215–218.
**Signature:** `guessColInfoForImports(values: CellValue[], docData: DocData): GuessColMetadata`.
**Data Shape:** `GuessColMetadata = { values: CellValue[], colMetadata?: ColMetadata }` — colMetadata omitted means "no changes proposed".

### Decisive source
```ts
if (values.every(v => (v === null || v === ""))) {
  // Suggest empty column.
  return { values, colMetadata: { type: "Any", isFormula: true, formula: "" } };
}
if (values.some(isObject)) {
  // Suggest no changes.
  return { values };
}
const strValues = values.map(v => (v === null || typeof v === "string" ? v : String(v)));
const guessed = guessColInfoWithDocData(strValues, docData);
values = guessed.values || values;
const opts = guessed.colInfo.widgetOptions;
const colMetadata = { ...guessed.colInfo, widgetOptions: opts && JSON.stringify(opts) };
if (!colMetadata.widgetOptions) {
  delete colMetadata.widgetOptions;   // Omit widgetOptions unless it is actually valid JSON.
}
```

**Flow:** every cell null/"" ⇒ propose a formula-less empty Any column (cheap placeholder that never stores junk) → ANY structured object in the data vetoes guessing entirely (objects are already typed; re-coercion risks mangling lists/lookups) → else stringify non-strings and run the standard lossless ladder; converted VALUES ride back alongside metadata so AddTable applies them atomically.
**Invariant:** The empty-column proposal is `isFormula:true` — meaning future edits compute, not store. widgetOptions must be JSON-STRING because it travels inside AddColumn user-action payloads (`MetaRowRecord` fields are strings); an absent options object must be physically DELETED, not left as undefined/null, since downstream treats presence as intent. A porter serializing `{}` here creates columns with broken option parsing.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/platforms/grist-core && grep -n "isFormula: true, formula: \"\"" app/common/ValueGuesser.ts && grep -n "delete colMetadata.widgetOptions" app/common/ValueGuesser.ts'` → :205 and :218.
Direct tests: `test/common/ValueGuesser.ts` :211 `describe("guessColInfoForImports")` (empty/object/typed cases).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"guessColInfoForImports colMetadata widgetValues import","limit":4,"detail":"ids"}'
```

## Verdict
Adopt the three-way gate and the JSON-string-or-delete rule verbatim (wire-format contract); adapt the Any/isFormula vocabulary to your schema model; omit the object veto only if your importer already routes objects elsewhere.
