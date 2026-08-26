<!-- capsule-v2 -->
# Lossless type-guess ladder — in what order should imported string columns be tried for Bool/Numeric/Date conversion, and when must the column stay Text?

**Source:** grist-core Apache-2.0 `main@c057666bb93b6f93a69b0884ce023676c3a2804b`; Codebase Memory `grist-core`. **Question:** When a column of raw strings arrives (CSV import, paste), how does Grist decide its column type without ever losing information?

## guessColInfo tries Bool → Numeric → Date, then falls back to Text WITHOUT returning values
**Path/Symbol:** `app/common/ValueGuesser.ts`: `guessColInfo` (:176–195), `guessColInfoWithDocData` (:172–174), final fallback `{ colInfo: { type: "Text" } }` (:193).
**Signature:** `guessColInfo(values: (string|null)[], docSettings: DocumentSettings, timezone: string): GuessResult`.
**Data Shape:** `GuessResult = { values?: CellValue[], colInfo: { type, widgetOptions? } }`. `values` omitted ⇒ caller keeps original strings. Doc settings + doc timezone come from `docData.docSettings()` / `docData.docInfo().timezone`.

### Decisive source
```ts
return (
  new BoolGuesser()
    .guess(values, docSettings) ||
    new NumericGuesser(
      docSettings,
      NumberParse.fromSettings(docSettings).guessOptions(values),
    )
      .guess(values, docSettings) ||
      new DateGuesser(guessDateFormat(values, timezone), timezone)
        .guess(values, docSettings) ||
  // Don't return the same values back if there's no conversion to be done,
  // as they have to be serialized and transferred over a pipe to Python.
        { colInfo: { type: "Text" } }
);
```

**Flow:** BoolGuesser (exact `"true"`/`"false"` strings only) → NumericGuesser seeded with format options voted from the data itself (`NumberParse.guessOptions`) → DateGuesser seeded with a format guessed by `guessDateFormat` → Text fallback. Each `.guess()` returns null on any doubt, which `||`-short-circuits into the next candidate.
**Invariant:** The whole ladder is LOSSLESS: a guessed type is adopted only if every parsed value formats back to exactly the input string (see ninety-percent-parse-budget). A porter who guesses "Numeric" for `["1","01"]` breaks the invariant — leading zeros would not survive formatting, so it stays Text. The Text fallback deliberately omits `values` because re-serializing unchanged strings across the JS→Python pipe costs bandwidth for nothing.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/platforms/grist-core && grep -n "type: \"Text\"" app/common/ValueGuesser.ts && grep -n "new BoolGuesser()" app/common/ValueGuesser.ts'` → :193 (single Text fallback) and :182 (Bool first).
Direct tests: `test/common/ValueGuesser.ts` (:15 `describe("ValueGuesser")`; "should guess booleans and numbers correctly" :16; date guessing :126).

### Retrieve
```bash
codebase-memory-mcp cli search_graph '{"project":"grist-core","query":"ValueGuesser guessColInfo BoolGuesser NumericGuesser DateGuesser","limit":6,"detail":"ids"}'
```

## Verdict
Adopt the precedence ladder (cheapest strictest type first) and the omit-values Text fallback; adapt the concrete type names/widget option shapes to your schema vocabulary; omit the docSettings plumbing only if your host has no per-doc locale.
